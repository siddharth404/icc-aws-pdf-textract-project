# Automated PDF Processing Using AWS Serverless Architecture
**Course:** Cloud Computing  
**Project Type:** Event-Driven Serverless Data Pipeline  
**Submission Date:** February 14, 2026

---

## Abstract
This project presents an implementation of an event-driven, serverless architecture designed to automate the extraction of structured data from unstructured PDF documents. By utilizing **Function-as-a-Service (FaaS)** via AWS Lambda, **Machine Learning** via Amazon Textract, and **Message Queuing** via Amazon SNS and SQS, the system demonstrates the principles of decoupled microservices and elastic scalability. The architecture addresses the challenge of converting static document repositories into queryable datasets suitable for business intelligence analysis.

---

## 1. Problem Definition

### 1.1 Scope
Recruitment processes often involve the ingestion of large volumes of unstructured PDF resumes. Manual data extraction from these documents allows for downstream analysis but is resource-intensive and prone to transcription errors.

### 1.2 Objectives
The primary objective is to design a cloud-native system that:
1.  **Automates Data Extraction**: Converts unstructured PDF text into structured CSV format.
2.  **Implements Event-Driven Design**: Utilizes asynchronous triggers to handle variable workloads without provisioned infrastructure.
3.  **Optimizes Cost**: Leverages a pay-per-use model to minimize idle resource expenditure.

---

## 2. System Architecture

### 2.1 Architectural Pattern
The system follows a **Decoupled Asynchronous Pattern** to separate ingestion from processing:

1.  **Ingestion Layer**: S3 Bucket (`incoming/`) receives raw PDF files.
2.  **Event Trigger**: S3 Event Notification invokes the `SubmissionLambda`.
3.  **Asynchronous Integration**: `SubmissionLambda` initiates the Textract `StartDocumentAnalysis` API and terminates immediately (FaaS pattern).
4.  **Notification Layer**: Textract publishes job completion status to **Amazon SNS** (Simple Notification Service).
5.  **Buffering Layer**: **Amazon SQS** (Simple Queue Service) subscribes to the SNS topic, buffering messages to decouple production rate (Textract completion) from consumption rate (processing).
6.  **Processing Layer**: `ProcessingLambda` polls SQS, retrieves analysis results, and performs data transformation.
7.  **Storage Layer**: Structured data is persisted in S3 (`processed/`) and metadata in DynamoDB.

### 2.2 Key Design Decisions
-   **Asynchronous vs. Synchronous**: The synchronous `AnalyzeDocument` API is limited by a 60-second Lambda timeout and single-page processing. The asynchronous `StartDocumentAnalysis` API was selected to support multi-page documents and long-running jobs, aligning with the stateless nature of FaaS.
-   **Queue-Based Load Leveling**: The implementation of SQS acts as a buffer. In scenarios of high-concurrency uploads (burst traffic), the queue persists messages, allowing the `ProcessingLambda` to consume them at a controlled rate, thereby preventing throttling of downstream services.
-   **Fault Tolerance**: A **Dead Letter Queue (DLQ)** is configured to capture messages that fail processing after three attempts, ensuring data integrity and enabling root cause analysis of "poison pill" records.

---

## 3. Implementation Details

### 3.1 Submission Function (`SubmissionLambda`)
*   **Trigger**: `s3:ObjectCreated:*`
*   **Logic**: Validates the input file type and initiates the Textract asynchronous job.
*   **State Management**: Stateless; logs the `JobId` to CloudWatch for observability.

### 3.2 Processing Function (`ProcessingLambda`)
*   **Trigger**: `sqs:ReceiveMessage`
*   **Logic**:
    1.  Validates job status (`SUCCEEDED`).
    2.  Retrieves analysis results using `GetDocumentAnalysis`.
    3.  Implements pagination logic (`NextToken`) to reconstruct the full document object model.
    4.  Applies a confidence threshold filter (`Confidence >= 90.0%`) to extracted fields.
    5.  Transforms extracted key-value pairs into a standardized CSV schema.
    6.  Performs S3 lifecycle operations (move to `archive/` or `error/`).

---

## 4. Data Schema

The system outputs data in a normalized CSV format.

| Field Name | Data Type | Constraint | Null Handling |
| :--- | :--- | :--- | :--- |
| **Name** | String | None | Empty String |
| **Email** | String | Validated Format | Empty String |
| **Phone** | String | None | Empty String |
| **Skills** | String | Delimited List | Empty String |
| **University** | String | None | Empty String |
| **Degree** | String | None | Empty String |
| **Experience** | String | None | Empty String |

**Note**: Data storage follows a "Data Lake" approach (Object Storage), where each processed document corresponds to a single object in the `processed/` prefix.

---

## 5. Cost Analysis

**Assumptions**:
*   Workload: 10,000 pages per month.
*   Region: us-east-1.

### 5.1 Service Breakdown
1.  **Amazon Textract (Queries Feature)**:
    *   Unit Cost: $15.00 per 1,000 pages.
    *   Monthly Cost: $(10,000 / 1,000) \times 15.00 = \$150.00$
2.  **AWS Lambda (Compute)**:
    *   Invocations: 20,000 (10k Submission + 10k Processing).
    *   Duration: ~2,100ms total processing time per document.
    *   Memory: 128 MB.
    *   Compute Time: $20,000 \times 2.1s = 42,000s$.
    *   GB-Seconds: $42,000s \times 0.125GB = 5,250 \text{ GB-s}$.
    *   **Cost**: Within AWS Free Tier (400,000 GB-s/month).
3.  **Amazon S3 (Storage & Requests)**:
    *   Storage: ~5GB.
    *   Request Costs: Minimal (<$1.00).

### 5.2 Total Estimated Monthly Cost
**Total: ~$150.50**

*Conclusion*: The cost structure is dominated by the Machine Learning service (Textract). The serverless infrastructure contributes a negligible amount to the total operational expense.

---

## 6. Scalability Analysis

### 6.1 Theoretical Throughput
Throughput in a FaaS architecture is constrained by the concurrent execution limit of the account.

$$ T = \frac{C \times 1000}{D} $$

Where:
*   $T$ = Throughput (requests/second)
*   $C$ = Concurrency Limit (Default: 1,000)
*   $D$ = Average Execution Duration (ms)

Given an average processing duration ($D$) of approximately 2,000ms:

$$ T = \frac{1000 \times 1000}{2000} = 500 \text{ documents/second} $$

### 6.2 Application to Requirements
To process 10,000 documents per day:
*   Required Throughput: $\frac{10,000}{86,400} \approx 0.12 \text{ documents/second}$.
*   **Conclusion**: The default concurrency limits provide capacity significantly exceeding the requirement.

---

## 7. Security & Compliance

### 7.1 Data Security
*   **Encryption at Rest**: S3 implementation uses Server-Side Encryption (SSE-S3) with AES-256.
*   **Encryption in Transit**: All service interactions occur over TLS 1.2 channels.

### 7.2 Access Control
*   **Principle of Least Privilege**: IAM roles are scoped strictly.
    *   `SubmissionLambda`: `s3:PutObject`, `textract:StartDocumentAnalysis`.
    *   `ProcessingLambda`: `sqs:ReceiveMessage`, `s3:PutObject`.
    *   **Public Access**: Blocked for all processed data buckets.

---

## 8. System Limitations

1.  **OCR Confidence**: Extraction accuracy is dependent on input quality. Documents scanned below 150 DPI may yield confidence scores below the 90% threshold, resulting in null fields.
2.  **Handwriting Recognition**: While supported, performance on cursive handwriting is variable compared to printed text.
3.  **Cold Starts**: Lambda initialization latency may impact the first request in a burst, though this is termed acceptable for asynchronous batch processing.

---

## 9. Appendix: Analytics

Integration with **Amazon Athena** (interactive query service) and **Amazon QuickSight** (BI visualization) allows for the querying of the S3-resident CSV data. Refer to `docs/analytics_guide.md` for the setup configuration.

---
*End of Submission*
