import os
import json
import boto3

def handler(event, context):
    
    print(json.dumps(event))
    
    data = {}
    rds_client = boto3.client('rds')

    cluster_resp = rds_client.describe_db_clusters(
        DBClusterIdentifier = os.environ['REGIONAL_APP_DB_CLUSTER_IDENTIFIER']
    )
        
    for member in cluster_resp['DBClusters'][0]['DBClusterMembers']:
        
        instance_resp = rds_client.describe_db_instances(
            DBInstanceIdentifier = member['DBInstanceIdentifier']
        )
        
        data[member['DBInstanceIdentifier']] = {
            'az': instance_resp['DBInstances'][0]['AvailabilityZone'],
            'type': 'WRITER' if member['IsClusterWriter'] is True else 'READER'
        }
        
    return {
        'code': 200,
        'body': json.dumps(data)
    }