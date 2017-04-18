#!/bin/bash -ex

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

# Start Jenkins
service jenkins start

# Create initial admin user
until $(curl -s -m 60 -o /dev/null -I -f -u "admin:$(cat /var/lib/jenkins/secrets/initialAdminPassword)" http://localhost:8080/cli/); do printf "."; sleep 1; done
echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("admin", "Password123")' | java -jar /var/cache/jenkins/war/WEB-INF/jenkins-cli.jar -s "http://localhost:8080/" -noKeyAuth groovy = --username admin --password "$(cat /var/lib/jenkins/secrets/initialAdminPassword)"

# Restart Jenkins
service jenkins restart
