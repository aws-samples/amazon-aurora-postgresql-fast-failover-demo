import sys
sys.path.append('/opt')

import os
import json
import psycopg2
import multi_region_db

custom_functions = multi_region_db.Functions()
        
def handler(event, context):
    
    print(json.dumps(event))
    
    demo_db_credentials = custom_functions.get_db_credentials('App')
    
    try:
        
        db_conn = psycopg2.connect(
            host = os.environ['REGIONAL_APP_DB_CLUSTER_WRITER_ENDPOINT'],
            port = demo_db_credentials['port'],
            user = demo_db_credentials['username'],
            password = demo_db_credentials['password'],
            database = demo_db_credentials['database'],
            connect_timeout = 3,
            sslmode = 'require',
        )
            
        curs = db_conn.cursor()
        
        with db_conn:
     
            with db_conn.cursor() as curs:
     
                curs.execute('SELECT NOW()')
                results = curs.fetchall()
                db_conn.commit()
        
        curs.close()
        db_conn.close()
    
        status_code = 200
    
    except Exception as e:

        print('here')
        status_code = 500
    
    return {
        'code': status_code,
        'body': status_code,
    }