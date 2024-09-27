import sys
sys.path.append('/opt')

import os
import json
import boto3
import psycopg2
import dateutil.tz
import multi_region_db
from datetime import datetime
from botocore.exceptions import ClientError as boto3_client_error

custom_functions = multi_region_db.Functions()

def initiate_global_cluster_failover():
    
    rds_client = boto3.client('rds')
    
    try:
        
        print('Attempting to Retrieve Global DB Cluster Members: "' + os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'] + '"')
            
        describe_cluster_resp = rds_client.describe_global_clusters(
            GlobalClusterIdentifier = os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER']
        )
        
        '''
            For each Global Cluster member
        '''
        for cluster_member in describe_cluster_resp['GlobalClusters'][0]['GlobalClusterMembers']:
            
                '''
                    If there's a member in the failover region
                '''
                if os.environ['FAILOVER_REGION_NAME'] in cluster_member['DBClusterArn']:
                    
                    try:
                        
                        print('Attempting to Promote Regional Cluster "' + cluster_member['DBClusterArn'] + '" within Global DB Cluster "' + os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'] + '"')
                        
                        rds_client.failover_global_cluster(
                            GlobalClusterIdentifier = os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'],
                            TargetDbClusterIdentifier = cluster_member['DBClusterArn'],
                            AllowDataLoss = True
                        )
                        
                        print('Successfully Promoted Regional Cluster "' + cluster_member['DBClusterArn'] + '" within Global DB Cluster "' + os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'] + '"')
                    
                    except boto3_client_error as e:
                        raise Exception('Failed to Promote Regional Cluster within Global DB Cluster: ' + str(e))
                
    except boto3_client_error as e:
        raise Exception('Failed to Retrieve Global Cluster Members: ' + str(e))
                    
    return True
    
def log_failover_event():
    
    demo_db_credentials = custom_functions.get_db_credentials('Demo')
    
    db_conn = psycopg2.connect(
        host = os.environ['REGIONAL_DEMO_DB_CLUSTER_WRITER_ENDPOINT'],
        port = demo_db_credentials['port'],
        user = demo_db_credentials['username'],
        sslmode = 'require',
        password = demo_db_credentials['password'],
        database = demo_db_credentials['database'],
        connect_timeout = 3,
    )
    
    eastern = dateutil.tz.gettz('US/Eastern')
    
    curs = db_conn.cursor()
    curs.execute("INSERT INTO failoverevents (event,insertedon) values (2,'" + datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
    db_conn.commit()
    
    curs.close()
    db_conn.close()
   
def handler(event, context):
    
    print(json.dumps(event))
    
    initiate_global_cluster_failover()
            
    log_failover_event()