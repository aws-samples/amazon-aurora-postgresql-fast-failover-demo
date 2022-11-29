import sys
import subprocess

subprocess.call('pip install cfnresponse -t /tmp/ --no-cache-dir'.split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')

import io
import os
import json
import boto3
import cfnresponse
from botocore.exceptions import ClientError, ParamValidationError

'''
    - Region | str
    - ExportPrefix | str
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    boto3Session = boto3.Session(
        region_name = arguments['Region']
    )
    
    cfn_client = boto3Session.client('cloudformation')
    
    if event['RequestType'] in ['Create', 'Update']:
        
        try:
            
            response = cfn_client.list_exports()
            
            for export in response['Exports']:
            	
                if export['Name'].startswith(arguments['ExportPrefix']):
                    response_data[export['Name'].replace(arguments['ExportPrefix'] + '-', '')] = export['Value']
                
            print(response_data)
            
            return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
                
        except ClientError as e:
            print('Failed to Retrieve CFN Exports: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    if event['RequestType'] in ['Delete']:
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)