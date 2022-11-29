import sys
sys.path.append('/opt')
import subprocess

import os
import json
import boto3
import psycopg2
import cfnresponse
from botocore.exceptions import ClientError as boto3_client_error

'''
    RDSAdminSecretARN
'''
def handler(event, context):
    
    print(json.dumps(event))
    
    arguments = event['ResourceProperties']['Properties']
    operation = event['ResourceProperties']['Type'].replace('Custom::', '')
    
    response_data = {}
    
    rds_client = boto3.client('rds')
    secrets_manager_client = boto3.client('secretsmanager')

    try:
        
        get_secret_value_response = secrets_manager_client.get_secret_value(
            SecretId = arguments['RDSAdminSecretARN']
        )
        
    except boto3_client_error as e:
        print('Unable to retrieva RDS secret: ' + str(e))
        return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
        
    else:
        rds_secret = json.loads(get_secret_value_response['SecretString'])
    
    if event['RequestType'] in ['Create']:
        
        try:
            
            try:
                    
                db_conn = psycopg2.connect(
                    host = rds_secret['host'],
                    port = rds_secret['port'],
                    user = rds_secret['username'],
                    password = rds_secret['password'],
                    database = rds_secret['database'],
                    connect_timeout = 3,
                    sslmode = 'require',
                )
                
                curs = db_conn.cursor()
                
                ddl_statements = [
                    '''
                    CREATE SEQUENCE data_sequence start 1 increment 1;
                    ''',
                    '''
                    CREATE TABLE IF NOT EXISTS dataserver (
                        id integer not null primary key default nextval('data_sequence'),
                        guid VARCHAR(255) NOT NULL,
                        insertedon timestamp NOT NULL DEFAULT NOW(),
                        migratedon timestamp NOT NULL DEFAULT NOW()
                    );
                    ''',
                    '''
                    CREATE TABLE IF NOT EXISTS public.dataclient (
                        guid character varying(255) COLLATE pg_catalog."default" NOT NULL,
                        useast1 integer NOT NULL,
                        useast2 integer NOT NULL,
                        http_code integer,
                        insertedon time without time zone
                    );
                    ''',
                    '''
                    CREATE TABLE IF NOT EXISTS public.failoverevents (
                        event integer NOT NULL,
                        insertedon timestamp without time zone NOT NULL
                    );
                    '''
                ]
                
                for ddl_statement in ddl_statements:
                    
                    curs.execute(ddl_statement.replace('\r','').replace('\n',' '))
                    db_conn.commit()
                
                curs.close()
                db_conn.close()
            
                return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
                
            except Exception as error:
                print('There was a problem executing the DDL statements: ' + str(error))
                return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
                
        except boto3_client_error as e:
            print('Failed to Prepare RDS Database: ' + str(e.response))
            return cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            
    if event['RequestType'] in ['Update', 'Delete']:
        
        return cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)