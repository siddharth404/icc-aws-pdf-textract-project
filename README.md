# Automated Resume Processor (Serverless HR Tech)

This project demonstrates a serverless pipeline for automatically processing candidate resumes using **Amazon Textract Queries**. It extracts structured data (Name, Email, Skills, etc.) from PDF resumes and provides a simple dashboard for HR teams.

## Architecture

The workflow is event-driven and serverless:

1.  **Upload**: HR User uploads a PDF resume via the web interface to **Amazon S3**.
2.  **Trigger**: **AWS Lambda** is triggered automatically.
3.  **Analyze**: Lambda calls **Amazon Textract (AnalyzeDocument)** with natural language Queries to extract specific fields.
4.  **Output**:
    *   **CSV**: Structured data is saved to `output/`.
    *   **Archive**: Original PDF is moved to `archive/`.
    *   **Logs**: Metadata is stored in **Amazon DynamoDB**.

## Prerequisites

*   AWS CLI installed and configured
*   Node.js & NPM (for CDK)
*   Python 3.9+
*   AWS CDK Toolkit (`npm install -g aws-cdk`)

## Deployment Steps

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Deploy the Stack**:
    ```bash
    cdk deploy
    ```

## Configuration

After deployment, note the `Outputs` from the terminal (BucketName, IdentityPoolId, WebUrl).

1.  Open `web/index.html`.
2.  Update the `BUCKET_NAME`, `REGION`, and `IDENTITY_POOL_ID` constants with your deployment values.
3.  Upload the updated frontend to S3:
    ```bash
    aws s3 cp web/index.html s3://<YOUR_BUCKET_NAME>/index.html
    ```

## Usage

1.  Open the `WebUrl` in your browser.
2.  Upload a Resume PDF.
3.  Wait 15-20 seconds.
4.  Refresh the list to see and download the generated CSV.

## Deliverables Included
*   **Architecture Diagram & Solution**: See `solution_overview.md`
*   **Sample Output**: See `sample_output.csv`
*   **Logic Description**: See `lambda/csv_processor/main.py`
