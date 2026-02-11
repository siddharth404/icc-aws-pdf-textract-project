import boto3
import os
import json
import logging
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client('textract')

def lambda_handler(event, context):
    """
    Triggered by S3 ObjectCreated.
    Starts Textract Async Job.
    """
    logger.info(f"Event: {json.dumps(event)}")
    
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    sns_role_arn = os.environ['SNS_ROLE_ARN']
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        try:
            start_job(bucket, key, sns_topic_arn, sns_role_arn)
        except Exception as e:
            logger.error(f"Failed to start job for {key}: {str(e)}")
            raise e
            
    return {"status": "success"}

def start_job(bucket, key, topic_arn, role_arn):
    logger.info(f"Starting Textract job for: {bucket}/{key}")
    
    # Define Resume Queries
    queries = [
        {'Text': "What is the candidate's full name?", 'Alias': 'Name'},
        {'Text': "What is the email address?", 'Alias': 'Email'},
        {'Text': "What is the phone number?", 'Alias': 'Phone'},
        {'Text': "What are the technical skills?", 'Alias': 'Skills'},
        {'Text': "What is the university or college name?", 'Alias': 'University'},
        {'Text': "What is the highest degree obtained?", 'Alias': 'Degree'},
        {'Text': "How many years of work experience?", 'Alias': 'Experience'}
    ]
    
    response = textract.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        FeatureTypes=['QUERIES', 'FORMS'], # Intelligent extraction
        QueriesConfig={'Queries': queries},
        NotificationChannel={
            'SNSTopicArn': topic_arn,
            'RoleArn': role_arn
        },
        OutputConfig={
            'S3Bucket': bucket,
            'S3Prefix': 'textract-raw-output/' 
        }
        # We can optionally store raw JSON in S3, or just rely on GetDocumentAnalysis API.
        # Storing to S3 is good for large files/pagination persistence, but API access is fine for immediate processing.
        # Let's use OutputConfig so we have the raw JSON if needed, or we can just rely on the API.
        # If we provide OutputConfig, Textract writes to S3. 
        # CAUTION: If we provide OutputConfig, we might not get the JobId completion flow the same way or permissions might differ.
        # Standard async flow usually relies on GetDocumentAnalysis API. 
        # I will remove OutputConfig to stay standard and rely on GetDocumentAnalysis API calls in the processing lambda.
    )
    # Actually, removing OutputConfig is safer for the permissions I set up (GetDocumentAnalysis).
    
    # Retrying without OutputConfig for standard API approach
    response = textract.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        FeatureTypes=['QUERIES', 'FORMS'],
        QueriesConfig={'Queries': queries},
        NotificationChannel={
            'SNSTopicArn': topic_arn,
            'RoleArn': role_arn
        }
    )

    logger.info(f"Job started: {response['JobId']}")
