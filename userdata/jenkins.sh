#!/bin/bash -x

# Config
export AWS_DEFAULT_REGION=eu-west-2
JENKINS_HOME=/var/lib/jenkins
S3_BACKUP=s3://oliviervg-jenkins/

# Update system
yum clean all
yum update -y

# Install dependencies
zypper install -y git

# Install Jenkins
zypper addrepo -f https://pkg.jenkins.io/opensuse-stable/ jenkins
zypper --gpg-auto-import-keys install -y jenkins

# Restore possible backup
if [[ $S3_BACKUP == */ ]]; then
    S3_BACKUP=$S3_BACKUP`aws s3 ls $S3_BACKUP|tail -1|awk '{print $NF}'`
fi
LOCAL_BACKUP=/tmp/`basename $S3_BACKUP`
aws s3 cp $S3_BACKUP $LOCAL_BACKUP
mkdir -p $JENKINS_HOME
tar zxf $LOCAL_BACKUP -C $JENKINS_HOME
rm -f $LOCAL_BACKUP

# Start Jenkins
systemctl enable jenkins
systemctl start jenkins

# Initial setup
if [[ ! -f /var/lib/jenkins/setup_complete ]]; then
    until $(curl -s -m 60 -o /dev/null -I -f -u "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" http://localhost:8080/cli/); do printf "."; sleep 1; done
    echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("admin", "Password123")' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -noKeyAuth groovy = --username admin --password "$(cat /var/lib/jenkins/secrets/initialAdminPassword)"
    touch /var/lib/jenkins/setup_complete
    systemctl restart jenkins
fi
