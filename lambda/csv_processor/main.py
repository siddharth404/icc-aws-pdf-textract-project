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
            process_invoice(bucket, key)
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            # Optional: Move to error folder
            return {"status": "error", "message": str(e)}

    return {"status": "success"}

def process_invoice(bucket, key):
    logger.info(f"Processing file: {key} from bucket: {bucket}")
    
    # 1. Call Textract
    response = textract.analyze_expense(
        Document={'S3Object': {'Bucket': bucket, 'Name': key}}
    )
    
    # 2. Extract Data
    csv_string = extract_csv_data(response)
    
    # 3. Save CSV
    csv_key = key.replace('uploads/', 'output/').replace('.pdf', '.csv')
    s3.put_object(Bucket=bucket, Key=csv_key, Body=csv_string)
    logger.info(f"Saved CSV to: {csv_key}")
    
    # 4. Log to DynamoDB
    table_name = os.environ.get('TABLE_NAME')
    if table_name:
        table = dynamodb.Table(table_name)
        table.put_item(Item={
            'InvoiceId': csv_key,
            'OriginalFile': key,
            'Status': 'PROCESSED'
        })
        
    # 5. Archive Original
    archive_key = key.replace('uploads/', 'archive/')
    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key}, Key=archive_key)
    s3.delete_object(Bucket=bucket, Key=key)
    logger.info(f"Archived to: {archive_key}")

def extract_csv_data(response):
    headers = ['Vendor', 'Date', 'Total', 'InvoiceNumber']
    rows = []
    
    for doc in response['ExpenseDocuments']:
        vendor = ""
        total = ""
        date = ""
        invoice_num = ""
        
        for field in doc['SummaryFields']:
            type_text = field['Type']['Text']
            value_text = field['ValueDetection']['Text']
            
            if type_text == 'VENDOR_NAME':
                vendor = value_text
            elif type_text == 'TOTAL':
                total = value_text
            elif type_text == 'INVOICE_RECEIPT_DATE':
                date = value_text
            elif type_text == 'INVOICE_RECEIPT_ID':
                invoice_num = value_text
                
        rows.append([vendor, date, total, invoice_num])
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()
