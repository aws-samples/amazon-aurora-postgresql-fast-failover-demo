import sys
sys.path.append('/opt')

import os
import json
import boto3
import cfnresponse
from botocore.exceptions import ClientError as boto3_client_error

'''
    FailoverClusterARN
    GlobalClusterIdentifier
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    #operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    if event['RequestType'] in ['Create', 'Update']:
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
        
    elif event['RequestType'] in ['Delete']:
        
        rds_client = boto3.client('rds')
        
        try:
            
            describe_cluster_resp = rds_client.describe_global_clusters(
                GlobalClusterIdentifier = arguments['GlobalClusterIdentifier']
            )
            
            '''
                For each Global Cluster member
            '''
            for cluster_member in describe_cluster_resp['GlobalClusters'][0]['GlobalClusterMembers']:
                
                '''
                    If this failover cluster is a member of the Global Cluster
                '''
                if arguments['FailoverClusterARN'] == cluster_member['DBClusterArn']:
                    
                    '''
                        We're goign to remove it from the global cluster.
                    '''
                    rds_client.remove_from_global_cluster(
                        DbClusterIdentifier = arguments['FailoverClusterARN'],
                        GlobalClusterIdentifier = arguments['GlobalClusterIdentifier'],
                    )
                    
                    '''
                        Now, we'll monitor the detachment and respond only after it's successful.
                    '''
                    while True:
                
                        failover_cluster_still_attached = False
                        
                        describe_cluster_resp = rds_client.describe_global_clusters(
                            GlobalClusterIdentifier = arguments['GlobalClusterIdentifier']
                        )
                        
                        '''
                            For each global cluster member
                        '''
                        for cluster_member in describe_cluster_resp['GlobalClusters'][0]['GlobalClusterMembers']:
                            
                            '''
                                If the failover cluster's identifier is present in this member's ARN
                            '''
                            if arguments['FailoverClusterARN'] == cluster_member['DBClusterArn']:
        
                                '''
                                    We'll consider the failover cluster still attached
                                '''
                                failover_cluster_still_attached = True
                        
                        if failover_cluster_still_attached is False:
                            break

                
        except boto3_client_error as e:
            print('Failed to Detach Failover Cluster: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    if event['RequestType'] in ['Update', 'Delete']:
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)