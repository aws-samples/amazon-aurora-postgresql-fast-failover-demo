import sys
sys.path.append('/opt')

import os
import json
import boto3
import multi_region_db

custom_functions = multi_region_db.Functions()

def handler(event, context):
    
    print(json.dumps(event))
    
    '''
        For each global database endpoint, we'll update it to point to the
        regional writer endpoint.
    '''
    for endpoint_type in ['READER', 'WRITER']:
        
        custom_functions.update_dns_record(
            fqdn            = os.environ['REGIONAL_APP_DB_' + endpoint_type + '_ENDPOINT'],
            new_value       = os.environ['REGIONAL_APP_DB_CLUSTER_' + endpoint_type + '_ENDPOINT'],
            hosted_zone_id  = os.environ['PRIVATE_HOSTED_ZONE_ID'],
        )
        
    return {
        'code': 200,
        'records': json.dumps([])
    }