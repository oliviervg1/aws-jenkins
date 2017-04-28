from troposphere import Ref, Base64, GetAtt, Output
from troposphere.ec2 import Tag
from troposphere.autoscaling import Tag as AsgTag
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration
from troposphere.autoscaling import BlockDeviceMapping, EBSBlockDevice
from troposphere.elasticloadbalancing import LoadBalancer, HealthCheck
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate

from stacker.blueprints.base import Blueprint


class ELB(Blueprint):

    VARIABLES = {
        "ElbName": {
            "type": str,
            "description": "Name of ELB"
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
        "Tags": {
            "type": dict,
            "description": "Tags to apply to resources"
        }
    }

    def create_elb(self):
        variables = self.get_variables()

        self.load_balancer = self.template.add_resource(LoadBalancer(
            "ElasticLoadBalancer",
            LoadBalancerName=variables["ElbName"],
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

        self.template.add_output(Output(
            "ElbName",
            Description="ELB name",
            Value=Ref(self.load_balancer)
        ))

        self.template.add_output(Output(
            "ElbDNS",
            Description="ELB DNS",
            Value=GetAtt(self.load_balancer, "DNSName")
        ))

    def create_template(self):
        self.create_elb()


class ASG(Blueprint):

    VARIABLES = {
        "PrivateSubnetIds": {
            "type": list,
            "description": "List of private subnets to spin up instances in"
        },
        "KeyName": {
            "type": str,
            "description": "Key name to use for SSH"
        },
        "ElbName": {
            "type": str,
            "description": "Name of ELB"
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
        }
    }

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
            LoadBalancerNames=[variables["ElbName"]],
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

    def create_template(self):
        self.create_autoscaling_group()
