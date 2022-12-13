import sys
sys.path.append('/opt')

import os
import json
import time
import boto3
import psycopg2
import dateutil.tz
import multi_region_db
from datetime import datetime
from datetime import timedelta
from botocore.exceptions import ClientError as boto3_client_error

rds_client = boto3.client('rds')

custom_functions = multi_region_db.Functions()

def disable_proxy_monitor_cron():
    
    print('Attempting to Disable Proxy Monitor Cron: "' + os.environ['PROXY_MONITOR_CRON_NAME'] + '"')
    
    try:
        
        boto3.client('events').disable_rule(
            Name = os.environ['PROXY_MONITOR_CRON_NAME']
        )
        
        print('Successfully Disabled Proxy Monitor Cron: "' + os.environ['PROXY_MONITOR_CRON_NAME'] + '"')
        
    except boto3_client_error as e:
        raise Exception('Failed to Disable Proxy Monitor Cron: ' + str(e))
        
    return True

def is_rds_proxy_target_available():
    
    print('Attempting to Retrieve Proxy Target Status for Proxy: "' + os.environ['REGIONAL_APP_DB_PROXY_NAME'] + '"')
    
    try:
        
        describe_proxy_targets_resp = rds_client.describe_db_proxy_targets(
            DBProxyName = os.environ['REGIONAL_APP_DB_PROXY_NAME'], 
            TargetGroupName = 'default'
        )
        
        print('Successfully Retrieved Proxy Target Status for Proxy: "' + os.environ['REGIONAL_APP_DB_PROXY_NAME'] + '"')
        
    except boto3_client_error as e:
        raise Exception('Failed to Retrieve Proxy Target Status: ' + str(e))
    
    print(describe_proxy_targets_resp)
    
    if "'State': 'AVAILABLE'" in str(describe_proxy_targets_resp):
        return True
    
    else:
        return False
        
def point_global_app_db_endpoints_to_failover_proxy():
    
    r53_client = boto3.client('route53')
        
    for endpoint_type in ['READER', 'WRITER']:
        
        custom_functions.update_dns_record(
            fqdn            = os.environ['GLOBAL_APP_DB_' + endpoint_type + '_ENDPOINT'],
            new_value       = os.environ['REGIONAL_APP_DB_PROXY_' + endpoint_type + '_ENDPOINT'],
            hosted_zone_id  = os.environ['PRIVATE_HOSTED_ZONE_ID'],
        )
        
    return True

def log_event():
    
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
    curs.execute("INSERT INTO failoverevents (event,insertedon) values (5,'" + datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
    db_conn.commit()
    
    curs.close()
    db_conn.close()

def handler(event, context):
    
    now = datetime.now()
    end = now + timedelta(seconds = 50)
    
    while (datetime.now() < end):
        
        try:
        
            if is_rds_proxy_target_available():
                
                print('Target is Registered and Available')
                
                log_event()
                
                disable_proxy_monitor_cron()
                
                point_global_app_db_endpoints_to_failover_proxy()
                
                break;
                
            else:
                print('Target is NOT Registered and Available')
                
        except Exception as e:
            print(str(e))
            time.sleep(10)