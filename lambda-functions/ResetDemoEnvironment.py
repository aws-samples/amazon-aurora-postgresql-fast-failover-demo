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

event_bridge_client = ec2_client = boto3.client('events', 
    region_name = os.environ['FAILOVER_REGION_NAME']
)

def point_service_fqdn_to_primary_web_alb():
    
    r53_client = boto3.client('route53')
        
    try:
        
        r53_client.change_resource_record_sets(
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
        raise Exception('Failed to Update DNS Record: ' + str(e))
    
    return True

def point_global_app_db_endpoints_to_primary_proxy():
    
    for endpoint_type in ['READER', 'WRITER']:
        
        custom_functions.update_dns_record(
            fqdn            = os.environ['GLOBAL_APP_DB_' + endpoint_type + '_ENDPOINT'],
            new_value       = os.environ['REGIONAL_APP_DB_PROXY_' + endpoint_type + '_ENDPOINT'],
            hosted_zone_id  = os.environ['PRIVATE_HOSTED_ZONE_ID'],
        )
    
def point_global_app_db_cluster_endpoints_to_primary_cluster():
    
    for endpoint_type in ['READER', 'WRITER']:
        
        custom_functions.update_dns_record(
            fqdn            = 'db.cluster.' + endpoint_type + '.' + os.environ['PUBLIC_FQDN'] + '.internal',
            new_value       = os.environ['REGIONAL_APP_DB_CLUSTER_' + endpoint_type + '_ENDPOINT'],
            hosted_zone_id  = os.environ['PRIVATE_HOSTED_ZONE_ID'],
        )
    
def allow_traffic_to_primary_db_cluster():
    
    ec2_client = boto3.client('ec2')
    
    try:
        
        ec2_client.replace_network_acl_entry(
            Egress = False, 
            Protocol = '-1',
            CidrBlock = '0.0.0.0/0',
            RuleAction = 'allow',
            RuleNumber = 100,
            NetworkAclId = os.environ['REGIONAL_APP_DB_NACL_ID'],
        )
        
    except boto3_client_error as e:
        raise Exception('Failed to Reset NACL: ' + str(e))

def prune_db_tables(db_identifier, table_names):
    
    db_credentials = custom_functions.get_db_credentials(db_identifier)
    
    db_conn = psycopg2.connect(
        host = os.environ['GLOBAL_' + db_identifier.upper() + '_DB_WRITER_ENDPOINT'],
        port = db_credentials['port'],
        user = db_credentials['username'],
        sslmode = 'require',
        password = db_credentials['password'],
        database = db_credentials['database'],
        connect_timeout = 3,
    )
    
    for table_to_prune in table_names:
        
        curs = db_conn.cursor()
        curs.execute('DELETE FROM ' + table_to_prune)
        db_conn.commit()
        
    curs.close()
    db_conn.close()
    
    return True

def disable_proxy_monitor_rule():
    
    try:
        
        event_bridge_client.disable_rule(
            Name = os.environ['PROXY_MONITOR_CRON_NAME']
        )
    
    except boto3_client_error as e:
        raise Exception('Failed to Disable Proxy Monitor Rule: ' + str(e))
            
    return True
    
def enable_database_canary_rule():
    
    try:
        
        event_bridge_client.enable_rule(
            Name = os.environ['DATABASE_CANARY_CRON_NAME']
        )
    
    except boto3_client_error as e:
        raise Exception('Failed to Enable Database Canary Rule: ' + str(e))
            
    return True

'''
    It is expected that this function will be run in the PRIMARY AWS region
'''
def handler(event, context):
    
    allow_traffic_to_primary_db_cluster()
    
    prune_db_tables('App', ['dataserver'])
    prune_db_tables('Demo', ['dataclient', 'failoverevents'])
    
    disable_proxy_monitor_rule()
    enable_database_canary_rule()
    point_service_fqdn_to_primary_web_alb()
    point_global_app_db_endpoints_to_primary_proxy()
    point_global_app_db_cluster_endpoints_to_primary_cluster()
    
    return {
        'code': 200,
        'body': json.dumps([])
    }