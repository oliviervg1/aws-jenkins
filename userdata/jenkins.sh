#!/bin/bash -x

# Config
export AWS_DEFAULT_REGION=eu-west-2
JENKINS_HOME=/var/lib/jenkins
S3_BACKUP_BUCKET=s3://oliviervg-jenkins/

# Update system
yum clean all
yum update -y

# Get Java 8
yum install -y java-1.8.0-openjdk
yum remove -y java-1.7.0-openjdk

# Install dependencies
yum install -y git

# Install Jenkins
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
yum install -y jenkins

# Restore possible backup
if [[ $S3_BACKUP_BUCKET == */ ]]; then
    S3_BACKUP_BUCKET=$S3_BACKUP_BUCKET`aws s3 ls $S3_BACKUP_BUCKET|tail -1|awk '{print $NF}'`
fi
LOCAL_BACKUP=/tmp/`basename $S3_BACKUP_BUCKET`
aws s3 cp $S3_BACKUP_BUCKET $LOCAL_BACKUP
mkdir -p $JENKINS_HOME
tar zxf $LOCAL_BACKUP -C $JENKINS_HOME
rm -f $LOCAL_BACKUP

# Enable backup script
cat >/usr/local/bin/jenkins_backup <<EOL
#!/bin/bash -e

S3_BACKUP_BUCKET=$S3_BACKUP_BUCKET
S3_BACKUP_FILENAME=\`date +%Y-%m-%d:%H:%M:%S\`.zip
LOCAL_BACKUP=/tmp/\`basename \$S3_BACKUP_FILENAME\`

tar -C $JENKINS_HOME -zcf \$LOCAL_BACKUP . \
    --exclude "config-history/" \
    --exclude "config-history/*" \
    --exclude "jobs/*/workspace*" \
    --exclude "jobs/*/builds/*/archive" \
    --exclude "plugins/*/*" \
    --exclude "plugins/*.bak" \
    --exclude "war" \
    --exclude "cache" \
    --exclude ".ssh/" \
    --exclude ".ssh/*"

aws --region eu-west-2 s3 cp \$LOCAL_BACKUP \$S3_BACKUP_BUCKET\$S3_BACKUP_FILENAME
rm -rf \$LOCAL_BACKUP
EOL
chown root:root /usr/local/bin/jenkins_backup
chmod 755 /usr/local/bin/jenkins_backup

# Schedule hourly backups
echo "0 * * * * root /usr/local/bin/jenkins_backup >> /var/log/jenkins_backup.log 2>&1" > /etc/cron.d/jenkins
chown root:root /etc/cron.d/jenkins
chmod 644 /etc/cron.d/jenkins
service crond restart

# Start Jenkins
service jenkins start

# Initial setup
if [[ ! -f /var/lib/jenkins/setup_complete ]]; then
    until $(curl -s -m 60 -o /dev/null -I -f -u "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" http://localhost:8080/cli/); do printf "."; sleep 1; done
    echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("admin", "Password123")' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -noKeyAuth groovy = --username admin --password "$(cat /var/lib/jenkins/secrets/initialAdminPassword)"
    touch /var/lib/jenkins/setup_complete
    service jenkins restart
fi
