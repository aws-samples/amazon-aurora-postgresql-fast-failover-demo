import sys
sys.path.append('/opt')

import os
import json
import uuid
import psycopg2
import datetime
import dateutil.tz
import urllib.request
import multi_region_db
from botocore.vendored import requests

custom_functions = multi_region_db.Functions()
        
def handler(event, context):
    
    print(json.dumps(event))
    
    guid = uuid.uuid4()
    
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

    curs = db_conn.cursor()
    
    curs.execute("INSERT INTO dataclient (guid, primary_region, failover_region, http_code, insertedon) VALUES ('{}', 0, 0, 0, '{}');".format(
        str(guid),
        datetime.datetime.now(tz = eastern).strftime("%m/%d/%Y %H:%M:%S")
    ))
    
    db_conn.commit()
    
    http_code = 200
    http_content = ''

    print('END guid: ' + str(guid))

    try:
        
        res = urllib.request.urlopen(
            urllib.request.Request(
                url = 'https://' + os.environ['PUBLIC_FQDN'] + '?guid=' + str(guid),
                method = 'GET',
            ),
            timeout = 5
        )
        
        http_code = res.status
        http_content = res.read().decode()
        
    except Exception as e:
        http_code = 500
        print('Client Web Request Failed :' + str(e))

    try: 

        if http_code > 200:
            http_content = ''
            
        curs = db_conn.cursor()
        
        curs.execute('''
            UPDATE dataclient SET
                primary_region  = {},
                failover_region = {},
                http_code       = {}
            WHERE guid = '{}'
        '''.format(
            1 if http_content == os.environ['PRIMARY_REGION_NAME'] else 0,
            1 if http_content == os.environ['FAILOVER_REGION_NAME'] else 0,
            http_code,
            str(guid)
        ))
        
        db_conn.commit()
        
    except Exception as ex:
        http_code = 500
        print('Failed to Update Client Request: ' + str(ex) + ' - HTTP Content: "' + http_content + '"')
    
    curs.close()
    db_conn.close()
    
    return True