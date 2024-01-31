import sys
import subprocess

subprocess.call('pip install cfnresponse -t /tmp/ --no-cache-dir'.split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')

import io
import os
import json
import boto3
import shutil
import cfnresponse
from zipfile import ZipFile
from botocore.exceptions import ClientError as boto3_client_error

def zip_directory(path):
    
    for root, dirs, files in os.walk(path):
        
        for f in files:
            
            full_path = os.path.join(root, f)
            archive_name = full_path[len(path) + len(os.sep):]
            yield full_path, archive_name
            
def make_zip_file_bytes(path):
    
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for full_path, archive_name in zip_directory(path = path):
            z.write(full_path, archive_name)
    
    return buf.getvalue()
    
'''
    - Region | str
    - Packages | list
    - LayerName | str
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    boto3Session = boto3.Session(
        region_name = arguments['Region']
    )
                
    lambda_client = boto3Session.client('lambda')
    
    if event['RequestType'] in ['Create', 'Update']:
        
        subprocess.call(('pip install ' + ' '.join(arguments['Packages']) + ' -t /tmp/lambda-layer --no-cache-dir').split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        
        shutil.copyfile(os.path.realpath(__file__), '/tmp/lambda-layer/multi_region_db.py')
        
        try:
            
            response = lambda_client.publish_layer_version(
                LayerName = arguments['LayerName'],
                Content = {
                    'ZipFile': make_zip_file_bytes('/tmp/lambda-layer')
                },
                CompatibleRuntimes = [
                    'python3.9',
                    'python3.10',
                    'python3.11',
                    'python3.12',
                ],
                CompatibleArchitectures = [
                    'x86_64', 'arm64',
                ]
            )
            
            return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, response['LayerVersionArn'])
        
        except boto3_client_error as e:
            print('Failed to Deploy Lambda Layer: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    if event['RequestType'] in ['Delete']:
        
        try:
            
            layer_versions_response = lambda_client.list_layer_versions(
                LayerName = arguments['LayerName'],
            )
            
            for version in layer_versions_response['LayerVersions']:
                
                response = lambda_client.delete_layer_version(
                    LayerName = arguments['LayerName'],
                    VersionNumber = version['Version']
                )

        except boto3_client_error as e:
            print('Failed to Delete Layer Versions: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

import dateutil.tz
from datetime import datetime	
from datetime import timedelta

class Functions:
    
    def __init__(self):
        
        ''
        
    def add_five_seconds(self, start_time):
        
        return (datetime.strptime(str(start_time), '%H:%M:%S') + timedelta(seconds = 5)).strftime("%H:%M:%S")
        
    def subtract_five_seconds(self, start_time):
    
        return (datetime.strptime(str(start_time), '%H:%M:%S') + timedelta(seconds =- 5)).strftime("%H:%M:%S")
        
    def add_time(self, label, data):
    
        eastern = dateutil.tz.gettz('US/Pacific')
        mynow = datetime.now(tz = eastern)
        #print((datetime.strptime(label[len(label) - 1], '%H:%M:%S') + timedelta(seconds = 9)))
        #print(datetime.strptime(mynow.strftime("%H:%M:%S"), '%H:%M:%S'))
        
        while((datetime.strptime(label[len(label)-1], '%H:%M:%S') + timedelta(seconds = 9)) < datetime.strptime(mynow.strftime("%H:%M:%S"), '%H:%M:%S')):
            
            label.pop(0)
            data.pop(0)
            
            label.append(self.add_five_seconds(label[len(label) - 1]))
            data.append('0')
    
    '''
        Requires "REGIONAL_(APP|DEMO)_DB_SECRET_ARN" as an environment variable
        
        - db_identifier | str (App|Demo)
    '''
    def get_db_credentials(self, db_identifier):
    
        secrets_manager_client = boto3.client('secretsmanager')
        
        try:
            
            get_secret_value_response = secrets_manager_client.get_secret_value(
                SecretId = os.environ['REGIONAL_' + db_identifier.upper() + '_DB_SECRET_ARN']
            )
            
        except boto3_client_error as e:
            raise Exception('Failed to Retrieve ' + db_identifier + ' Database Secret: ' + str(e))
            
        else:
            return json.loads(get_secret_value_response['SecretString'])
            
    '''
        fqdn | str
        newValue | str
        hostedZoneId | str
        [ ttl | int ]
        [ type | str ]
    '''
    def update_dns_record(self, fqdn, new_value, hosted_zone_id, ttl = 1, record_type = 'CNAME'):
        
        r53_client = boto3.client('route53')
        
        try:
            
            r53_client.change_resource_record_sets(
                ChangeBatch = {
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': fqdn,
                                'ResourceRecords': [
                                    {
                                        'Value': new_value,
                                    },
                                ],
                                'TTL': ttl,
                                'Type': record_type,
                            },
                        },
                    ],
                },
                HostedZoneId = hosted_zone_id,
            )
            
        except boto3_client_error as e:
            raise Exception('Failed to Update DNS Record: ' + str(e))
            
        return True