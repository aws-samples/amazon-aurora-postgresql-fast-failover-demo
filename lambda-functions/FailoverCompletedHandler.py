import sys
sys.path.append('/opt')

import os
import json
import boto3
import psycopg2
import dateutil.tz
import multi_region_db
from datetime import datetime
from datetime import timedelta
from botocore.exceptions import ClientError as boto3_client_error

custom_functions = multi_region_db.Functions()

def enable_proxy_target_waiter_rule():
    
    print('Attempting to Enable Proxy Target Waiter Cron: "' + os.environ['PROXY_MONITOR_CRON_NAME'] + '"')

    try:
        
        boto3.client('events').enable_rule(
            Name = os.environ['PROXY_MONITOR_CRON_NAME']
        )
        
        print('Successfully Enabled Proxy Target Waiter Cron: "' + os.environ['PROXY_MONITOR_CRON_NAME'] + '"')
        
    except boto3_client_error as e:
        raise Exception('Failed to Enable Proxy Target Waiter Cron: ' + str(e))
    
def point_service_fqdn_to_failover_web_alb():
    
    try:

        boto3.client('route53').change_resource_record_sets(
            ChangeBatch = {
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': os.environ['PUBLIC_FQDN'],
                            'AliasTarget': {
                                'DNSName': os.environ['REGIONAL_WEB_ALB_FQDN'],
                                'HostedZoneId': os.environ['REGIONAL_WEB_ALB_HOSTED_ZONE_ID'],
                                'EvaluateTargetHealth': False
                            },
                            'Type': 'A'
                        },
                    },
                ],
            },
            HostedZoneId = os.environ['PUBLIC_HOSTED_ZONE_ID'],
        )
        
    except boto3_client_error as e:
        raise Exception('Failed to Update ALB DNS Record: ' + str(e))

def register_failover_cluster_as_proxy_target():
    
    try:
        
        boto3.client('rds').register_db_proxy_targets(
            DBProxyName             = os.environ['REGIONAL_APP_DB_PROXY_NAME'],
            TargetGroupName         = 'default',
            DBClusterIdentifiers    = [
                os.environ['REGIONAL_APP_DB_CLUSTER_IDENTIFIER']
            ]
        )
    
    except boto3_client_error as e:
        raise Exception('Failed to Register Failover Cluster as Proxy Target: ' + str(e))
        
def handler(event, context):
    
    print(json.dumps(event))
    
    eastern = dateutil.tz.gettz('US/Eastern')
    
    demo_db_credentials = custom_functions.get_db_credentials('Demo')

    db_conn = psycopg2.connect(
        host = os.environ['GLOBAL_DEMO_DB_WRITER_ENDPOINT'],
        port = demo_db_credentials['port'],
        user = demo_db_credentials['username'],
        password = demo_db_credentials['password'],
        database = demo_db_credentials['database'],
        connect_timeout = 3,
        sslmode = 'require',
    )
    
    current_region = os.environ['AWS_REGION']
    
    if current_region == os.environ['PRIMARY_REGION_NAME']:
        
        curs = db_conn.cursor()
        curs.execute("INSERT INTO failoverevents (event,insertedon) values (3,'" + datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
        db_conn.commit()
        
    elif current_region == os.environ['FAILOVER_REGION_NAME']:
        
        dns_changes = [
            {
                'fqdn': os.environ['GLOBAL_APP_DB_WRITER_ENDPOINT'],
                'newValue': os.environ['REGIONAL_APP_DB_CLUSTER_WRITER_ENDPOINT'],
                'hostedZoneId': os.environ['PRIVATE_HOSTED_ZONE_ID'],
            },
            {
                'fqdn': os.environ['GLOBAL_APP_DB_READER_ENDPOINT'],
                'newValue': os.environ['REGIONAL_APP_DB_CLUSTER_READER_ENDPOINT'],
                'hostedZoneId': os.environ['PRIVATE_HOSTED_ZONE_ID'],
            }
        ]
        
        for dns_change in dns_changes:
            
            custom_functions.update_dns_record(
                fqdn            = dns_change['fqdn'],
                new_value       = dns_change['newValue'],
                hosted_zone_id  = dns_change['hostedZoneId'],
            )
            
        enable_proxy_target_waiter_rule()
        
        point_service_fqdn_to_failover_web_alb()
        
        register_failover_cluster_as_proxy_target()
      
    '''
        Logs CNAME Update
    '''
    curs = db_conn.cursor()
    curs.execute("INSERT INTO failoverevents (event,insertedon) values (4,'" + datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
    db_conn.commit()
    
    '''
        Logs Failover Completion
    '''
    curs = db_conn.cursor()
    curs.execute("INSERT INTO failoverevents (event,insertedon) values (3,'" + datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "' )")
    db_conn.commit()
        
    curs.close()
    db_conn.close()
    
    return True