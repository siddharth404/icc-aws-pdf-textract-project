import boto3
import json
import logging
import os
import csv
import io
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client('textract')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    Triggered by SQS Message (from SNS Notification).
    """
    logger.info(f"Event: {json.dumps(event)}")
    
    for record in event['Records']:
        try:
            # SQS Body -> SNS Message -> Textract Message
            sqs_body = json.loads(record['body'])
            sns_message = json.loads(sqs_body['Message'])
            
            job_id = sns_message['JobId']
            status = sns_message['Status']
            document_location = sns_message['DocumentLocation']
            bucket = document_location['S3Bucket']
            key = document_location['S3ObjectName']
            
            logger.info(f"Processing Job: {job_id}, Status: {status}, Key: {key}")
            
            if status == 'SUCCEEDED':
                process_succeeded_job(job_id, bucket, key)
            else:
                handle_failure(bucket, key, f"Textract Status: {status}")
                
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            # In a real system, might want to DLQ this message if it's retryable.
            # Lambda + SQS automatically retries on exception.
            # We raise so Lambda doesn't delete the message immediately if it's transient.
            # BUT if it's a code error, we might get stuck in a loop. 
            # For this demo, let's log and swallow to avoid infinite loop on bad message structure.
            # If valid S3 key existed, we try to move to error folder.
            continue 

    return {"status": "success"}

def process_succeeded_job(job_id, bucket, key):
    # 1. Get Analysis Results (Pagination)
    blocks = []
    next_token = None
    
    while True:
        params = {'JobId': job_id}
        if next_token:
            params['NextToken'] = next_token
            
        response = textract.get_document_analysis(**params)
        blocks.extend(response['Blocks'])
        
        next_token = response.get('NextToken')
        if not next_token:
            break
            
    # 2. Extract Data
    data = extract_intelligent_data(blocks)
    
    # 3. Create CSV
    csv_string = generate_csv(data)
    
    # 4. Save to Processed
    # key is likely "incoming/file.pdf"
    filename = os.path.basename(key) 
    csv_key = f"processed/{filename.replace('.pdf', '.csv')}"
    
    s3.put_object(Bucket=bucket, Key=csv_key, Body=csv_string)
    logger.info(f"Saved CSV to {csv_key}")
    
    # 5. Archive Original
    archive_key = f"archive/{filename}"
    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key}, Key=archive_key)
    s3.delete_object(Bucket=bucket, Key=key)
    logger.info(f"Archived PDF to {archive_key}")
    
    # 6. Update DynamoDB
    table_name = os.environ.get('TABLE_NAME')
    if table_name:
        table = dynamodb.Table(table_name)
        table.put_item(Item={
            'ResumeId': csv_key, # Using CSV path as ID
            'OriginalFile': archive_key,
            'Status': 'PROCESSED',
            'CompletionTime': str(int(time.time())),
            'JobId': job_id,
            'ExtractedData': data # specific fields
        })

def handle_failure(bucket, key, reason):
    logger.error(f"Job Failed for {key}: {reason}")
    filename = os.path.basename(key)
    error_key = f"error/{filename}"
    
    # Move to error folder
    try:
        s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key}, Key=error_key)
        s3.delete_object(Bucket=bucket, Key=key)
        
        # Write error log file
        s3.put_object(Bucket=bucket, Key=f"error/{filename}.log", Body=reason)
    except Exception as e:
        logger.error(f"Failed to move to error folder: {str(e)}")

def extract_intelligent_data(blocks):
    """
    Extracts key-value pairs from Queries.
    Filters by confidence score > 90.
    """
    key_map = {} # ID -> Alias
    value_map = {} # ID -> Text
    confidence_map = {} # ID -> Confidence
    
    for block in blocks:
        if block['BlockType'] == 'QUERY':
            if 'Query' in block and 'Alias' in block['Query']:
                key_map[block['Id']] = block['Query']['Alias']
        elif block['BlockType'] == 'QUERY_RESULT':
             value_map[block['Id']] = block['Text']
             confidence_map[block['Id']] = block.get('Confidence', 0)

    # Required Fields
    headers = ['Name', 'Email', 'Phone', 'Skills', 'University', 'Degree', 'Experience']
    data = {h: '' for h in headers}
    
    # Link Answers
    for block in blocks:
        if block['BlockType'] == 'QUERY':
            alias = block['Query'].get('Alias')
            if alias in data and 'Relationships' in block:
                for rel in block['Relationships']:
                    if rel['Type'] == 'ANSWER':
                        for id in rel['Ids']:
                            if id in value_map:
                                conf = confidence_map.get(id, 0)
                                if conf > 90: # High confidence filter
                                    data[alias] = value_map[id]
                                else:
                                    logger.warning(f"Low confidence ({conf}%) for {alias}: {value_map[id]}")
    return data

def generate_csv(data):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data.keys())
    writer.writeheader()
    writer.writerow(data)
    return output.getvalue()
