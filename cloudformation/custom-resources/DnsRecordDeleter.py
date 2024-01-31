import sys
import subprocess

subprocess.call('pip install cfnresponse -t /tmp/ --no-cache-dir'.split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')

import json
import boto3
import cfnresponse
from botocore.exceptions import ClientError, ParamValidationError

'''
    - Fqdns | list 
    - HostedZoneId | str
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    route53_client = boto3.client('route53')
    
    if event['RequestType'] in ['Delete']:
        
        try:
            
            record_sets_resp = route53_client.list_resource_record_sets(
                HostedZoneId = arguments['HostedZoneId'],
            )
            
            change_batch = []
            
            for record_set in record_sets_resp['ResourceRecordSets']:
                
                print(record_set)
                
                '''
                    We'll be leaving NS and SOA records.
                '''
                if record_set['Type'] in ['NS', 'SOA']:
                    print('Not An Eligible Record Type - Skipping')
                    continue
                
                '''
                    If we've been instructed to delete all FQDNs or this FQDN
                    
                    We're going to use for comparison the raw record name from Route53
                    as well as the name minus the trailing period.
                '''
                if '*' in arguments['Fqdns'] or (record_set['Name'] in arguments['Fqdns'] or record_set['Name'][0:-1] in arguments['Fqdns']):
                    
                    print('Deleting Record')
                    
                    change_batch.append({
                        'Action': 'DELETE',
                        'ResourceRecordSet': record_set,
                    })
            
            if len(change_batch) > 0:
                
                route53_client.change_resource_record_sets(
                    HostedZoneId = arguments['HostedZoneId'],
                    ChangeBatch = {
                        'Changes': change_batch
                    }
                )
                
        except ClientError as e:
            
            print('Failed to Delete DNS Records: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)