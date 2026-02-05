# Simplified Receipt Processor with Amazon Textract

This project demonstrates a serverless invoice processing pipeline tailored for educational purposes. It uses a simplified architecture to extract data from PDF invoices using Amazon Textract and convert it into CSV format.

## Architecture

The workflow is streamlined to use minimal AWS services for ease of understanding and deployment:

1. **Upload**: Users upload PDF invoices via a static web interface directly to an **Amazon S3** bucket (secured via **Amazon Cognito**).
2. **Trigger**: An **AWS Lambda** function is triggered automatically when a new PDF is uploaded.
3. **Process**: The Lambda function calls **Amazon Textract** (AnalyzeExpense API) to extract key fields (Vendor, Date, Total, Invoice Number).
4. **Output**: The extracted data is formatted as a CSV file and saved back to the S3 bucket in an `output/` folder.
5. **Archive**: The original PDF is moved to an `archive/` folder to keep the upload area clean.

## Prerequisites

- AWS CLI installed and configured
- Node.js & NPM (for CDK)
- Python 3.9+
- AWS CDK Toolkit (`npm install -g aws-cdk`)

## Deployment Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/aws-samples/amazon-textract-invoice-processor.git
   cd amazon-textract-invoice-processor/code
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy the Stack**
   ```bash
   # Bootstrap CDK (only needed once per region)
   cdk bootstrap

   # Deploy the changes
   cdk deploy
   ```

## Post-Deployment Configuration

After a successful deployment, you will see `Outputs` in your terminal. You need these to configure the web frontend.

1. **Locate Outputs**: Look for `BucketName`, `IdentityPoolId`, and `WebUrl` in the `Outputs` section.
2. **Update Frontend**:
   - Open `web/index.html`.
   - Replace the `YOUR_BUCKET_NAME_HERE` and `us-east-1:xxxxxx-xxxx-xxxx-xxxx-xxxxxx` placeholders with the values from your deployment outputs.
   - Also ensure `REGION` matches your deployment region (e.g., `us-east-1`).
3. **Deploy Frontend**:
   - Upload the modified `index.html` to your S3 bucket to serve the website.
   ```bash
   aws s3 cp web/index.html s3://<YOUR_BUCKET_NAME>/index.html
   ```

## Usage

1. **Open the Web App**: Find the `WebUrl` output from the deployment (or navigate to the S3 bucket's website endpoint).
2. **Upload Invoice**: Click "Choose File" to select a PDF invoice and click "Upload PDF".
3. **Wait & Refresh**: The processing takes a few seconds. Click "Refresh List" to see the generated `.csv` files.
4. **Download**: Click on a CSV file to download the extracted data.

## Cleanup

To avoid incurring future charges, delete the resources:

1. **Empty the S3 Bucket** (CDK cannot delete a non-empty bucket):
   ```bash
   aws s3 rm s3://<YOUR_BUCKET_NAME> --recursive
   ```
2. **Destroy the Stack**:
   ```bash
   cdk destroy
   ```

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
