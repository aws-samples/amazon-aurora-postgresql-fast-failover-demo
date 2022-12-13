import sys
sys.path.append('/opt')

import os
import time
import json
import boto3
import urllib
import psycopg2
import dateutil.tz
import multi_region_db
from datetime import datetime
from datetime import timedelta
from botocore.exceptions import ClientError as boto3_client_error

custom_functions = multi_region_db.Functions()

app_db_credentials = custom_functions.get_db_credentials('App')

def test_db_via_api():
    
    res = urllib.request.urlopen(
        urllib.request.Request(
            url = 'https://api.' + os.environ['PUBLIC_FQDN'] + '/perform-health-check',
            method = 'GET',
    ),
        timeout = 5
    )
        
    if int(res.read()) == 500:
        raise Exception('Health Check Failed')

def test_db_connection():

    db_conn = psycopg2.connect(
        host = os.environ['GLOBAL_APP_DB_WRITER_ENDPOINT'],
        port = app_db_credentials['port'],
        user = app_db_credentials['username'],
        sslmode = 'require',
        password = app_db_credentials['password'],
        database = app_db_credentials['database'],
        connect_timeout = 3,
    )
    
    with db_conn:
        with db_conn.cursor() as curs:
            curs.execute('SELECT NOW()')
            results = curs.fetchall()
            db_conn.commit()
        
def disable_canary_rule():
    
    print('Attempting to Disable Database Canary Cron: "' + os.environ['DATABASE_CANARY_CRON_NAME'] + '"')

    try:
        
        boto3.client('events').disable_rule(
            Name = os.environ['DATABASE_CANARY_CRON_NAME']
        )
        
        print('Successfully Disabled Database Canary Cron: "' + os.environ['DATABASE_CANARY_CRON_NAME'] + '"')
        
    except boto3_client_error as e:
        
        raise Exception('Failed to Disable Database Canary Cron: ' + str(e))
        
    return True

def detach_and_promote_failover_cluster():
    
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
                    If this failover cluster is a member of the Global Cluster
                '''
                if os.environ['REGIONAL_APP_DB_CLUSTER_ARN'] == cluster_member['DBClusterArn']:
                    
                    try:
                        
                        print('Attempting to Detach Regional Cluster "' + os.environ['REGIONAL_APP_DB_CLUSTER_ARN'] + '" from Global DB Cluster "' + os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'] + '"')
                        
                        rds_client.remove_from_global_cluster(
                            DbClusterIdentifier = os.environ['REGIONAL_APP_DB_CLUSTER_ARN'],
                            GlobalClusterIdentifier = os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'],
                        )
                        
                        print('Successfully Detached Regional Cluster "' + os.environ['REGIONAL_APP_DB_CLUSTER_ARN'] + '" from Global DB Cluster "' + os.environ['GLOBAL_APP_DB_CLUSTER_IDENTIFIER'] + '"')
                    
                    except boto3_client_error as e:
                        raise Exception('Failed to Detach Failover Cluster from Global Cluster: ' + str(e))
                
    except boto3_client_error as e:
        raise Exception('Failed to Retrieve Global Cluster Members: ' + str(e))
                    
    return True
    
def log_failover_event():
    
    demo_db_credentials = custom_functions.get_db_credentials('Demo')
    
    db_conn = psycopg2.connect(
        host = os.environ['GLOBAL_DEMO_DB_WRITER_ENDPOINT'],
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
    
    failures = 0
    end_time = datetime.now() + timedelta(seconds = 60)
    
    while (datetime.now() < end_time):
        
        try:
            
            #test_db_via_api()
            test_db_connection()
            
        except Exception as e:
            
            failures += 1
            print('Failed to Establish DB Connection')
        
        if failures > 1:
            
            print('Connection Failure Tolerance Exceeded')
            
            detach_and_promote_failover_cluster()
            
            disable_canary_rule()
            
            log_failover_event()
            
            return False
            
        time.sleep(10)
    
    return True