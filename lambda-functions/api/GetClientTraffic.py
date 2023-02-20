import sys
sys.path.append('/opt')

import os
import json
import psycopg2	
import dateutil.tz
import multi_region_db
from datetime import datetime	
from datetime import timedelta

custom_functions = multi_region_db.Functions()

def handler(event, context):
    
    print(json.dumps(event))
    
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
    
    if event['queryParams']['region'] not in ['primary', 'failover']:
        raise Exception('Invalid Region Specified')
        
    curs = db_conn.cursor()	
    
    curs.execute('''
        SELECT
            insertedon,
            sum(CASE WHEN http_code = 200 AND {}_region = 1 THEN 1 ELSE 0 END)
        FROM dataclient
        WHERE http_code != 0
        GROUP BY insertedon
        ORDER BY insertedon
        DESC limit 15
    '''.format(event['queryParams']['region']))
    
    traffic_records = curs.fetchall()
    
    curs.close()	
    db_conn.close()
    
    data_json = ""
    label_json = ""
    	
    data_arr = []	
    label_arr = []	
    
    if event['queryParams']['region'] == 'primary':
        
        for i in reversed(range(1, len(traffic_records))):	
            
            data_arr.append(str(traffic_records[i][1]))	
            label_arr.append(str(traffic_records[i][0]))
            
    elif event['queryParams']['region'] == 'failover':
    	
        for i in reversed(traffic_records):
            
            data_arr.append(str(i[1]))
            label_arr.append(str(i[0]))
        	
    if len(label_arr) > 0:
        
        for n in range(len(label_arr) + 1, 16):	
            
            data_arr.insert(0, '0')
            label_arr.insert(0, custom_functions.subtract_five_seconds(label_arr[0]))	
        	
        custom_functions.add_time(label_arr,data_arr)	
    	
    i =- 1	
    for r in label_arr:	
        i = i + 1	
        if label_json != "":	
            label_json += ","	
        if data_json != "":	
            data_json += ","	
            	
        data_json += data_arr[i]	
        label_json += label_arr[i]	
    	
    return {
        'code': 200,
        'body': json.dumps([{
            'data': data_json,
            'labels': label_json,
        }])
    }	