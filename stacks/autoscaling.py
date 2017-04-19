from troposphere import Ref, Base64, GetAtt
from troposphere.ec2 import Tag
from troposphere.autoscaling import Tag as AsgTag
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration
from troposphere.autoscaling import BlockDeviceMapping, EBSBlockDevice
from troposphere.elasticloadbalancing import LoadBalancer, HealthCheck
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
from troposphere.route53 import RecordSetGroup, RecordSet

from stacker.blueprints.base import Blueprint


class AppWithDns(Blueprint):

    VARIABLES = {
        "AppName": {
            "type": str,
            "description": "Name of application"
        },
        "ElbPublicSubnetIds": {
            "type": list,
            "description": (
                "List of public subnets to spin up ELBs in"
            )
        },
        "ElbListeners": {
            "type": list,
            "description": "List of ELB listeners"
        },
        "ElbSecurityGroups": {
            "type": list,
            "description": "List of ELB security groups"
        },
        "ElbHealthcheck": {
            "type": dict,
            "description": "ELB healthcheck"
        },
        "PrivateSubnetIds": {
            "type": list,
            "description": "List of private subnets to spin up instances in"
        },
        "KeyName": {
            "type": str,
            "description": "Key name to use for SSH"
        },
        "ImageId": {
            "type": str,
            "description": "Base AMI to use"
        },
        "InstanceType": {
            "type": str,
            "description": "EC2 instance size to use"
        },
        "AsgSecurityGroups": {
            "type": list,
            "description": "List of ELB security groups"
        },
        "VolumeSize": {
            "type": int,
            "description": "Size of EBS volume"
        },
        "IamInstanceProfile": {
            "type": str,
            "description": "IAM role to attach to instance"
        },
        "Userdata": {
            "type": str,
            "description": "Path to userdata script"
        },
        "Tags": {
            "type": dict,
            "description": "Tags to apply to resources"
        },
        "HostedZoneName": {
            "type": str,
            "description": "Hosted Zone to create DNS in"
        },
        "DNS": {
            "type": str,
            "description": "DNS for application"
        }
    }

    def create_elb(self):
        variables = self.get_variables()

        self.load_balancer = self.template.add_resource(LoadBalancer(
            "ElasticLoadBalancer",
            LoadBalancerName="{}-elb".format(variables["AppName"]),
            Subnets=variables["ElbPublicSubnetIds"],
            Listeners=variables["ElbListeners"],
            SecurityGroups=variables["ElbSecurityGroups"],
            HealthCheck=HealthCheck(
                **variables["ElbHealthcheck"]
            ),
            CrossZone=True,
            Tags=[
                Tag(key, value)
                for key, value in variables["Tags"].iteritems()
            ]
        ))

    def create_autoscaling_group(self):
        variables = self.get_variables()

        with open(variables["Userdata"]) as f:
            userdata = f.read()

        launch_configuration = self.template.add_resource(LaunchConfiguration(
            "LaunchConfiguration",
            UserData=Base64(userdata),
            ImageId=variables["ImageId"],
            KeyName=variables["KeyName"],
            SecurityGroups=variables["AsgSecurityGroups"],
            InstanceType=variables["InstanceType"],
            IamInstanceProfile=variables["IamInstanceProfile"],
            AssociatePublicIpAddress="false",
            BlockDeviceMappings=[
                BlockDeviceMapping(
                    DeviceName="/dev/xvda",
                    Ebs=EBSBlockDevice(
                        DeleteOnTermination=True,
                        VolumeSize=variables["VolumeSize"],
                        VolumeType="gp2"
                    )
                )
            ]
        ))

        self.template.add_resource(AutoScalingGroup(
            "AutoscalingGroup",
            LaunchConfigurationName=Ref(launch_configuration),
            MinSize="1",
            MaxSize="1",
            VPCZoneIdentifier=variables["PrivateSubnetIds"],
            LoadBalancerNames=[Ref(self.load_balancer)],
            UpdatePolicy=UpdatePolicy(
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime="PT0S",
                    MinInstancesInService="0",
                    MaxBatchSize="1"
                )
            ),
            Tags=[
                AsgTag(key, value, True)
                for key, value in variables["Tags"].iteritems()
            ]
        ))

    def create_dns(self):
        variables = self.get_variables()

        self.template.add_resource(RecordSetGroup(
            "DNS",
            HostedZoneName=variables["HostedZoneName"],
            RecordSets=[
                RecordSet(
                    Name=variables["DNS"],
                    ResourceRecords=[GetAtt(self.load_balancer, "DNSName")],
                    Type="CNAME",
                    TTL=300
                )
            ]
        ))

    def create_template(self):
        self.create_elb()
        self.create_autoscaling_group()
        self.create_dns()
