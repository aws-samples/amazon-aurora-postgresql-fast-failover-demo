import sys
sys.path.append('/opt')

import os
import json
import boto3
import datetime
import psycopg2
import dateutil.tz
import multi_region_db
from botocore.exceptions import ClientError as boto3_client_error

custom_functions = multi_region_db.Functions()

def handler(event, context):
    
    print(json.dumps(event))
    
    http_status_code = 200
    
    try: 
        
        guid = event['queryStringParameters']['guid']

        eastern = dateutil.tz.gettz('US/Eastern')

        sql_statement = "INSERT INTO dataserver (guid, insertedon) VALUES ('" + str(guid) + "','" + datetime.datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S") + "') RETURNING id"
        
        app_db_credentials = custom_functions.get_db_credentials('App')
        
        db_conn = psycopg2.connect(
            host = os.environ['REGIONAL_APP_DB_CLUSTER_WRITER_ENDPOINT'],
            port = app_db_credentials['port'],
            user = app_db_credentials['username'],
            password = app_db_credentials['password'],
            database = app_db_credentials['database'],
            connect_timeout = 3,
            sslmode = 'require',
        )
        
        id = 0
        http_status_code = 200
        curs = db_conn.cursor()
        curs.execute(sql_statement)
        id = curs.fetchone()[0]
        print(id)
        db_conn.commit()
        curs.close()
        db_conn.close()
        
    except Exception as e:
        http_status_code = 500
        print(e)
        
    return {
        'statusCode': http_status_code,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': os.environ['AWS_REGION']
    }