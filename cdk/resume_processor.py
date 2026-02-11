from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_events
)
from constructs import Construct

class ResumeProcessorWorkflow(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 Bucket
        bucket = s3.Bucket(
            self, "ResumeBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            website_index_document="index.html",
            public_read_access=True, # WARNING: For Student Demo ONLY
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.HEAD],
                allowed_origins=["*"],
                allowed_headers=["*"]
            )]
        )

        # 2. DynamoDB Table
        table = dynamodb.Table(
            self, "ResumeMetadata",
            partition_key=dynamodb.Attribute(name="ResumeId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3. SNS Topic for Textract Notifications
        textract_topic = sns.Topic(self, "TextractTopic", display_name="Textract Completion Topic")

        # 4. SQS Queue for Buffering
        dlq = sqs.Queue(self, "TextractDLQ")
        textract_queue = sqs.Queue(
            self, "TextractQueue",
            visibility_timeout=Duration.seconds(300), # Must be > Lambda timeout
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq)
        )
        # Subscribe SQS to SNS
        textract_topic.add_subscription(subs.SqsSubscription(textract_queue))
        
        # 5. Service Role for Textract to publish to SNS
        textract_role = iam.Role(
            self, "TextractServiceRole",
            assumed_by=iam.ServicePrincipal("textract.amazonaws.com")
        )
        # Allow Textract to publish to the SNS topic
        textract_topic.grant_publish(textract_role)

        # 6. Submission Lambda (Triggers Textract)
        submission_fn = _lambda.Function(
            self, "SubmissionLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="main.lambda_handler",
            code=_lambda.Code.from_asset("lambda/submission"),
            timeout=Duration.seconds(30),
            environment={
                "SNS_TOPIC_ARN": textract_topic.topic_arn,
                "SNS_ROLE_ARN": textract_role.role_arn
            }
        )
        
        # Permissions for Submission
        bucket.grant_read(submission_fn)
        # Must specifically allow valid textract actions
        submission_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:StartDocumentAnalysis"],
            resources=["*"]
        ))
        submission_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["iam:PassRole"],
            resources=[textract_role.role_arn]
        ))
        # Add S3 Trigger on 'incoming/'
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(submission_fn),
            s3.NotificationKeyFilter(prefix="incoming/", suffix=".pdf")
        )


        # 7. Processing Lambda (Workers)
        processing_fn = _lambda.Function(
            self, "ProcessingLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="main.lambda_handler",
            code=_lambda.Code.from_asset("lambda/processing"),
            timeout=Duration.seconds(120),
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # SQS Trigger for Processing
        # batch_size=1 means one document at a time to avoid complex partial batch failure handling for now
        processing_fn.add_event_source(lambda_events.SqsEventSource(textract_queue, batch_size=1))

        # Permissions for Processing
        bucket.grant_read_write(processing_fn)
        table.grant_read_write_data(processing_fn)
        processing_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:GetDocumentAnalysis"],
            resources=["*"]
        ))
        
        # 8. Cognito (Guest Access) - Kept from original for Web Uploads
        identity_pool = cognito.CfnIdentityPool(
            self, "ResumeIdentityPool",
            allow_unauthenticated_identities=True
        )
        unauth_role = iam.Role(
            self, "CognitoDefaultUnauthRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {"StringEquals": {"cognito-identity.amazonaws.com:aud": identity_pool.ref},
                 "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "unauthenticated"}},
                "sts:AssumeRoleWithWebIdentity"
            )
        )
        unauth_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
            resources=[bucket.bucket_arn, bucket.bucket_arn + "/*"]
        ))
        cognito.CfnIdentityPoolRoleAttachment(
            self, "DefaultValid",
            identity_pool_id=identity_pool.ref,
            roles={"unauthenticated": unauth_role.role_arn}
        )

        # 9. Outputs
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "QueueUrl", value=textract_queue.queue_url)
        CfnOutput(self, "SNSTopicArn", value=textract_topic.topic_arn)
        CfnOutput(self, "WebUrl", value=bucket.bucket_website_url)
        CfnOutput(self, "IdentityPoolId", value=identity_pool.ref)
