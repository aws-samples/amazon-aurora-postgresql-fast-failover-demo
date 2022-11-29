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

def delete_all_objects(bucket_name):
    
    try:
            
        boto3.resource('s3').Bucket(bucket_name).objects.all().delete()
    
    except boto3_client_error as e:
        print('Failed to Empty Dashboard Bucket: ' + str(e))
        return False
    
    return True
    
'''
    - CodeBucketName | str
    - CodeDownloadURL | str
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    response_data = {}
    
    if event['RequestType'] in ['Create', 'Update']:
        
        path_to_local_zip = '/tmp/dashboard_code.zip'
        path_to_local_dir = path_to_local_zip.replace('.zip', '')
        
        '''
            Download the codebase
        '''
        http = urllib3.PoolManager()
        code_download_response = http.request('GET', arguments['CodeDownloadURL'], preload_content = False)
        
        if code_download_response.status != 200:
            return False
        
        with code_download_response as r, open(path_to_local_zip, 'wb') as out_file:
            shutil.copyfileobj(r, out_file)
        
        '''
            Unzip the downloaded code
        '''
        with zipfile.ZipFile(path_to_local_zip, 'r') as zip_ref:
            zip_ref.extractall(path_to_local_dir)
            
        s3_client = boto3.client('s3')
        
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
                    
        properties = event['ResourceProperties']
        
    elif event['RequestType'] in ['Delete']:
        
        object_deletion = delete_all_objects(arguments['CodeBucketName'])
        
        delete_marker_deletion = True
        #delete_marker_deletion = delete_all_delete_markers(arguments['CodeBucketName'])
        
        if object_deletion is False or delete_marker_deletion is False:
                
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
    
    return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)