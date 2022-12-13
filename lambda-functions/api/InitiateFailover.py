import sys
sys.path.append('/opt')

import os
import json
import boto3
import psycopg2
import datetime
import dateutil.tz
import multi_region_db
from botocore.exceptions import ClientError as boto3_client_error

custom_functions = multi_region_db.Functions()

def trigger_failover():
    
    try:
        
        boto3.client('rds').failover_db_cluster(
            DBClusterIdentifier = os.environ['REGIONAL_APP_DB_CLUSTER_IDENTIFIER']
        )
        
    except boto3_client_error as e:
        raise Exception('Failed to Initiate Cluster Failover: ' + str(e))
        
def log_failover_event():
    
    eastern = dateutil.tz.gettz('US/Eastern')
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

    curs = db_conn.cursor()
    curs.execute("INSERT INTO failoverevents (event, insertedon) values (1,'" + datetime.datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
    db_conn.commit()
    
    curs.close()
    db_conn.close()
    
def handler(event, context):
    
    print(json.dumps(event))
    
    trigger_failover()

    log_failover_event()
    
    return {
        'code': 200,
        'body': []
    }