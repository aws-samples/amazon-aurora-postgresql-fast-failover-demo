import sys
import subprocess

subprocess.call('pip install cfnresponse -t /tmp/ --no-cache-dir'.split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')

import io
import os
import json
import boto3
import cfnresponse
from zipfile import ZipFile
from botocore.exceptions import ClientError, ParamValidationError

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
        
        try:
            
            response = lambda_client.publish_layer_version(
                LayerName = arguments['LayerName'],
                Content = {
                    'ZipFile': make_zip_file_bytes('/tmp/lambda-layer')
                },
                CompatibleRuntimes = [
                    'python3.9',
                ],
                CompatibleArchitectures = [
                    'x86_64', 'arm64',
                ]
            )
            
            return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data, response['LayerVersionArn'])
        
        except ClientError as e:
            print('Failed to Deploy Lambda Layer: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    if event['RequestType'] in ['Delete']:
        
        '''
        response = client.list_layer_versions(
            CompatibleRuntime='nodejs'|'nodejs4.3'|'nodejs6.10'|'nodejs8.10'|'nodejs10.x'|'nodejs12.x'|'nodejs14.x'|'java8'|'java8.al2'|'java11'|'python2.7'|'python3.6'|'python3.7'|'python3.8'|'python3.9'|'dotnetcore1.0'|'dotnetcore2.0'|'dotnetcore2.1'|'dotnetcore3.1'|'dotnet6'|'nodejs4.3-edge'|'go1.x'|'ruby2.5'|'ruby2.7'|'provided'|'provided.al2',
            LayerName='string',
            Marker='string',
            MaxItems=123,
            CompatibleArchitecture='x86_64'|'arm64'
        )
        
        for each layer version, delete it
        
        response = client.delete_layer_version(
            LayerName='string',
            VersionNumber=123
        )
        '''
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)