from troposphere.route53 import RecordSetGroup
from troposphere.route53 import RecordSet as TroposphereRecordSet

from stacker.blueprints.base import Blueprint


class RecordSet(Blueprint):

    VARIABLES = {
        "HostedZoneName": {
            "type": str,
            "description": "Hosted Zone to create DNS in"
        },
        "DNS": {
            "type": str,
            "description": "DNS entry for the application"
        },
        "ResourceRecords": {
            "type": list,
            "description": "List of DNS records to point to"
        },
        "Type": {
            "type": str,
            "description": "DNS type, e.g. CNAME, A, etc"
        },
        "TTL": {
            "type": int,
            "description": "Time to live"
        }
    }

    def create_dns(self):
        variables = self.get_variables()

        self.template.add_resource(RecordSetGroup(
            "DNS",
            HostedZoneName=variables["HostedZoneName"],
            RecordSets=[
                TroposphereRecordSet(
                    Name=variables["DNS"],
                    ResourceRecords=variables["ResourceRecords"],
                    Type=variables["Type"],
                    TTL=variables["TTL"]
                )
            ]
        ))

    def create_template(self):
        self.create_dns()
