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
            insertedon,
            sum(CASE WHEN http_code = 200 THEN 0 ELSE 1 END)
        FROM dataclient
        WHERE http_code != 0
        GROUP BY insertedon
        ORDER BY insertedon DESC
        LIMIT 15
    ''');
    client_errors = curs.fetchall()
    
    curs.close()
    db_conn.close()
    
    data_json = ""
    label_json = ""
    
    data_arr = []
    label_arr = []
    
    #for i in reversed(range(1,len(client_errors))):
    #    label_arr.append(str(client_errors[i][0]))
    #    data_arr.append(str(client_errors[i][1]))
    
    for r in reversed(client_errors):
        
        label_arr.append(str(r[0]))
        data_arr.append(str(r[1]))
        
    if len(label_arr) > 0:
        
        for n in range(len(label_arr) + 1, 16):
            
            label_arr.insert(0, custom_functions.subtract_five_seconds(label_arr[0]))
            data_arr.insert(0, '0')
        
        custom_functions.add_time(label_arr,data_arr)
    
    i =- 1
    for r in label_arr:
        i = i + 1
        if label_json!="":
            label_json+=","
        if data_json!="":
            data_json+=","
            
        data_json += data_arr[i]
        label_json += label_arr[i]
    
    return {
        'code': 200,
        'body': json.dumps([{
            'data': data_json,
            'labels': label_json, 
        }])
    }