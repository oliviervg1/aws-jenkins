from troposphere import Ref, Base64
from troposphere.ec2 import Tag
from troposphere.autoscaling import Tag as AsgTag
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration
from troposphere.autoscaling import BlockDeviceMapping, EBSBlockDevice
from troposphere.elasticloadbalancing import LoadBalancer, HealthCheck
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate

from stacker.blueprints.base import Blueprint


class AutoscalingGroup(Blueprint):

    VARIABLES = {
        "AppName": {
            "type": str,
            "description": "Name of application"
        },
        "ElbPublicSubnetIds": {
            "type": list,
            "description": (
                "List of public subnets to spin up the Jenkins ELBs in"
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
            "description": (
                "List of private subnets to spin up the Jenkins in"
            )
        },
        "KeyName": {
            "type": str,
            "description": "Key name to use for SSH"
        },
        "ImageId": {
            "type": str,
            "description": "Base AMI to use for Jenkins"
        },
        "InstanceType": {
            "type": str,
            "description": "EC2 instance size to use for Jenkins"
        },
        "AsgSecurityGroups": {
            "type": list,
            "description": "List of ELB security groups"
        },
        "VolumeSize": {
            "type": int,
            "description": "Size of EBS volume"
        },
        "Userdata": {
            "type": str,
            "description": "Path to userdata script"
        },
        "Tags": {
            "type": dict
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

    def create_template(self):
        self.create_elb()
        self.create_autoscaling_group()
