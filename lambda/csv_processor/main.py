import boto3
import csv
import io
import os
import logging
import json
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        try:
            process_resume(bucket, key)
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            # Optional: Move to error folder
            return {"status": "error", "message": str(e)}

    return {"status": "success"}

def process_resume(bucket, key):
    logger.info(f"Processing resume: {key} from bucket: {bucket}")
    
    # Define Queries
    queries = [
        {'Text': "What is the candidate's full name?", 'Alias': 'Name'},
        {'Text': "What is the email address?", 'Alias': 'Email'},
        {'Text': "What is the phone number?", 'Alias': 'Phone'},
        {'Text': "What are the technical skills?", 'Alias': 'Skills'},
        {'Text': "What is the highest degree or education?", 'Alias': 'Education'},
        {'Text': "How many years of experience?", 'Alias': 'Experience'}
    ]

    # 1. Call Textract with Queries
    response = textract.analyze_document(
        Document={'S3Object': {'Bucket': bucket, 'Name': key}},
        FeatureTypes=['QUERIES'],
        QueriesConfig={'Queries': queries}
    )
    
    # 2. Extract Data
    csv_string = extract_query_results(response)
    
    # 3. Save CSV
    csv_key = key.replace('uploads/', 'output/').replace('.pdf', '.csv')
    s3.put_object(Bucket=bucket, Key=csv_key, Body=csv_string)
    logger.info(f"Saved CSV to: {csv_key}")
    
    # 4. Log to DynamoDB
    table_name = os.environ.get('TABLE_NAME')
    if table_name:
        table = dynamodb.Table(table_name)
        table.put_item(Item={
            'ResumeId': csv_key,
            'OriginalFile': key,
            'Status': 'PROCESSED'
        })
        
    # 5. Archive Original
    archive_key = key.replace('uploads/', 'archive/')
    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key}, Key=archive_key)
    s3.delete_object(Bucket=bucket, Key=key)
    logger.info(f"Archived to: {archive_key}")

def extract_query_results(response):
    headers = ['Name', 'Email', 'Phone', 'Skills', 'Education', 'Experience']
    data = {h: '' for h in headers}
    
    # Map Alias to Value
    # Textract Query Response Structure:
    # Blocks of type QUERY_RESULT contain the answer Text.
    # We need to link QUERY blocks (which have the Alias) to QUERY_RESULT blocks (via Relationships).
    
    # Simplification for Synchronous AnalyzeDocument:
    # We can iterate through blocks, find QUERIES, check their alias, and find the corresponding result.
    
    blocks = response['Blocks']
    key_map = {} # ID -> Alias
    value_map = {} # ID -> Text
    
    for block in blocks:
        if block['BlockType'] == 'QUERY':
            if 'Query' in block and 'Alias' in block['Query']:
                key_map[block['Id']] = block['Query']['Alias']
        elif block['BlockType'] == 'QUERY_RESULT':
             value_map[block['Id']] = block['Text']
             
    # Now link them
    for block in blocks:
        if block['BlockType'] == 'QUERY':
            alias = block['Query'].get('Alias')
            if 'Relationships' in block:
                for rel in block['Relationships']:
                    if rel['Type'] == 'ANSWER':
                        # Usually one answer per query
                        for id in rel['Ids']:
                            if id in value_map:
                                data[alias] = value_map[id]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow([data[h] for h in headers])
    return output.getvalue()
