from troposphere import Ref, Output
from troposphere.ec2 import SecurityGroup as TroposphereSecurityGroup
from troposphere.ec2 import SecurityGroupRule
from troposphere.ec2 import Tag

from stacker.blueprints.base import Blueprint


class SecurityGroup(Blueprint):

    VARIABLES = {
        "Description": {
            "type": str,
            "description": "List of security group IDs to attach to ELB"
        },
        "VpcId": {
            "type": str,
            "description": "ID of VPC to create security group in"
        },
        "SecurityGroupIngress": {
            "type": list,
            "description": "Dictionary of inbound rules"
        },
        "SecurityGroupEgress": {
            "type": list,
            "description": "Dictionary of outbound rules"
        },
        "Tags": {
            "type": dict,
            "description": "List of tags to apply"
        }
    }

    def create_security_group(self):
        variables = self.get_variables()

        self.security_group = self.template.add_resource(
            TroposphereSecurityGroup(
                "SecurityGroup",
                GroupDescription=variables["Description"],
                VpcId=variables["VpcId"],
                SecurityGroupIngress=[
                    SecurityGroupRule(**rule)
                    for rule in variables["SecurityGroupIngress"]
                ],
                SecurityGroupEgress=[
                    SecurityGroupRule(**rule)
                    for rule in variables["SecurityGroupEgress"]
                ],
                Tags=[
                    Tag(key, value)
                    for key, value in variables["Tags"].iteritems()
                ]
            )
        )

        self.template.add_output(Output(
            "SecurityGroupId",
            Description="Security Group ID",
            Value=Ref(self.security_group)
        ))

    def create_template(self):
        self.create_security_group()
