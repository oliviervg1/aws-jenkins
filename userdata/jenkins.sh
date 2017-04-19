#!/bin/bash -x

# Config
export AWS_DEFAULT_REGION=eu-west-2
JENKINS_HOME=/var/lib/jenkins
S3_BACKUP=s3://oliviervg-jenkins/

# Update system
yum clean all
yum update -y

# Get Java 8
yum install -y java-1.8.0-openjdk
yum remove -y java-1.7.0-openjdk

# Install Jenkins
wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat/jenkins.repo
rpm --import http://pkg.jenkins-ci.org/redhat/jenkins-ci.org.key
yum install -y jenkins

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
service jenkins start

# Initial setup
if [[ ! -f /var/lib/jenkins/setup_complete ]]; then
    until $(curl -s -m 60 -o /dev/null -I -f -u "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" http://localhost:8080/cli/); do printf "."; sleep 1; done
    echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("admin", "Password123")' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -noKeyAuth groovy = --username admin --password "$(cat /var/lib/jenkins/secrets/initialAdminPassword)"
    touch /var/lib/jenkins/setup_complete
    service jenkins restart
fi
