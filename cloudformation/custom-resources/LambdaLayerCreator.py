import sys
sys.path.append('/opt')

import io
import os
import json
import boto3
import subprocess
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