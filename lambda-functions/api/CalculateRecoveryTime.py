import sys
sys.path.append('/opt')

import os
import json
import psycopg2
import multi_region_db

custom_functions = multi_region_db.Functions()

def handler(event, context):
    
    print(json.dumps(event))
    
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
    
    curs.execute('''
        SELECT
            DATE_PART('second', max(insertedon)::time - min(insertedon)::time) AS rto
        FROM dataclient 
        WHERE http_code = 500 
        GROUP BY http_code
    ''');
    
    client_events = curs.fetchall()
    
    curs.close()
    db_conn.close()
    
    records_to_return = []
    
    for client_event in client_events:
    
        c = 0
        temp2 = {}
        
        for col in curs.description:
            
            temp2.update({str(col[0]): client_event[c]})
            c += 1
        
        records_to_return.append(temp2)
    
    return {
        'code': 200,
        'body': json.dumps(records_to_return, default = str),
    }