import sys
sys.path.append('/opt')

import os
import json
import time
import boto3
import cfnresponse
from botocore.exceptions import ClientError as boto3_client_error

'''
    ClusterArn
    ClusterIdentifier
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    if event['RequestType'] in ['Delete']:
        
        rds_client = boto3.client('rds')
        
        try:
            
            '''
                First, we'll get the cluster's current status
            '''
            describe_cluster_resp = rds_client.describe_db_clusters(
                DBClusterIdentifier = arguments['ClusterArn'],
            )
            
            '''
                If there's a cluster matching this identifier
            '''
            if len(describe_cluster_resp) > 0:
                
                cluster_status = describe_cluster_resp['DBClusters'][0]['Status']
                
                '''
                    If the cluster's current status is AVAILABLE
                '''
                if cluster_status in ['available']:
                    
                    try:
                        
                        '''
                            We'll try to delete it
                        '''
                        rds_client.delete_db_cluster(
                            SkipFinalSnapshot = True,
                            DBClusterIdentifier = arguments['ClusterIdentifier']
                        )
                        
                        '''
                            Now, we'll monitor its deletion and respond only after it's successful.
                        '''
                        while True:
                            
                            try:
                                
                                describe_cluster_resp = rds_client.describe_db_clusters(
                                    DBClusterIdentifier = arguments['ClusterArn'],
                                )

                                time.sleep(5)
                                
                            except boto3_client_error as e:
                                
                                if e.response['Error']['Code'] == 'DBClusterNotFoundFault':
                                    return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
                                
                                else:
                                    print('Failed to Retrieve Cluster: ' + str(e.response))
                                    return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
                            
                    except boto3_client_error as e:
                        print('Failed to Delete Cluster: ' + str(e.response))
                        return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
                
        except boto3_client_error as e:
            print('Failed to Retrieve Cluster: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)

    return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)