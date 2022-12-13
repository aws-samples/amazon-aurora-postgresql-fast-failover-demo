import sys
import subprocess

subprocess.call('pip install cfnresponse -t /tmp/ --no-cache-dir'.split(), stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')

import os
import json
import glob
import boto3
import shutil
import urllib3
import zipfile
import mimetypes
import cfnresponse
from collections import defaultdict
from botocore.exceptions import ClientError as boto3_client_error

http = urllib3.PoolManager()

try:
    from urllib2 import HTTPError, build_opener, HTTPHandler, Request
except ImportError:
    from urllib.error import HTTPError
    from urllib.request import build_opener, HTTPHandler, Request
    
'''
    - CodeBucketName | str
    - CodeDownloadUrl | str
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    
    s3_client = boto3.client('s3')
    
    response_data = {}
    
    if event['RequestType'] in ['Create', 'Update']:
        
        path_to_local_zip = '/tmp/dashboard_code.zip'
        path_to_local_dir = path_to_local_zip.replace('.zip', '')
        
        '''
            Download the codebase
        '''
        http = urllib3.PoolManager()
        code_download_response = http.request('GET', arguments['CodeDownloadUrl'], preload_content = False)
        
        if code_download_response.status != 200:
            return False
        
        with code_download_response as r, open(path_to_local_zip, 'wb') as out_file:
            shutil.copyfileobj(r, out_file)
        
        '''
            Unzip the downloaded code
        '''
        with zipfile.ZipFile(path_to_local_zip, 'r') as zip_ref:
            zip_ref.extractall(path_to_local_dir)
            
        '''
            For each file in the local code directory
        '''
        for file_path in glob.iglob(path_to_local_dir + '**/**', recursive = True):
            
            '''
                If it's one of the dashboard files and it's a file, not a directory, we'll upload it to S3
            '''
            if '/dashboard/' in file_path and os.path.isfile(file_path):
            
                try:
                    
                    s3_key = file_path.split('/dashboard/')[1]
                    
                    s3_client.upload_file(file_path, arguments['CodeBucketName'], s3_key,
                        ExtraArgs = {
                            'ContentType': mimetypes.guess_type(file_path)[0]
                        })
                    
                except boto3_client_error as e:
                    print('Failed to Upload Dashboard File: ' + str(e))
                    return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
        
    elif event['RequestType'] in ['Delete']:
        
        '''
            Here, we'll delete all objects, versions, and delete markers from the bucket.
        '''
        object_response_paginator = s3_client.get_paginator('list_object_versions')
        
        objects_to_delete = []
        
        for object_response_iterator in object_response_paginator.paginate(Bucket = arguments['CodeBucketName']):
            
            for object_group in ['Versions', 'DeleteMarkers']:
                
                if object_group in object_response_iterator:
                
                    for object_data in object_response_iterator[object_group]:
                    
                        objects_to_delete.append({
                            'Key': object_data['Key'], 
                            'VersionId': object_data['VersionId']
                        })
                    
        for i in range(0, len(objects_to_delete), 1000):
            
            try:
                
                response = s3_client.delete_objects(
                    Bucket = arguments['CodeBucketName'],
                    Delete = {
                        'Objects': objects_to_delete[i:i + 1000],
                        'Quiet': True
                    }
                )
                
            except boto3_client_error as e:
                print('Failed to Delete S3 Objects: ' + str(e))
                return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
        
    return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)