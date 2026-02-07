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
    aws_cognito as cognito
)
from constructs import Construct

class ResumeProcessorWorkflow(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 Bucket (Resume storage, Public Access for Website)
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

        # 2. DynamoDB Table for Resume MetadataLogs
        table = dynamodb.Table(
            self, "ResumeMetadata",
            partition_key=dynamodb.Attribute(name="ResumeId", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3. Cognito Identity Pool (To allow "Guest" web uploads)
        identity_pool = cognito.CfnIdentityPool(
            self, "ResumeIdentityPool",
            allow_unauthenticated_identities=True
        )
        
        # Role for the Guest User
        unauth_role = iam.Role(
            self, "CognitoDefaultUnauthRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated"
                    }
                },
                "sts:AssumeRoleWithWebIdentity"
            )
        )
        
        # Grant specific permissions to the Guest Role (Upload ONLY)
        unauth_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
            resources=[bucket.bucket_arn, bucket.bucket_arn + "/*"]
        ))
        
        cognito.CfnIdentityPoolRoleAttachment(
            self, "DefaultValid",
            identity_pool_id=identity_pool.ref,
            roles={"unauthenticated": unauth_role.role_arn}
        )

        # 4. Textract/CSV Processor Lambda (Resume Logic)
        processor_fn = _lambda.Function(
            self, "resume-processor-fn",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="main.lambda_handler",
            code=_lambda.Code.from_asset("lambda/csv_processor"),
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # 5. Permissions
        bucket.grant_read_write(processor_fn)
        table.grant_read_write_data(processor_fn)
        
        # Updated Permissions for AnalyzeDocument (Queries)
        processor_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:AnalyzeDocument"],
            resources=["*"]
        ))

        # 6. S3 Trigger
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor_fn),
            s3.NotificationKeyFilter(prefix="uploads/", suffix=".pdf")
        )
        
        # 7. Outputs for Frontend
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "BucketRegion", value=Stack.of(self).region)
        CfnOutput(self, "IdentityPoolId", value=identity_pool.ref)
        CfnOutput(self, "WebUrl", value=bucket.bucket_website_url)
