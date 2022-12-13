import os
import time
import json
import boto3

def handler(event, context):
    
    print(json.dumps(event))

    sns_client = boto3.client('sns')
    
    for i in range(0, 10000):
        
        sns_client.publish(
            Message = 'Hola',
            TargetArn = os.environ['TEST_TRAFFIC_TOPIC_ARN'],
        )
        
        time.sleep(0.1)
    
    return {
        'code': 200,
        'body': json.dumps([])
    }
