# Automated PDF Processing Using AWS Serverless Architecture
**Course:** Cloud Computing & Distributed Systems (CS-550)  
**Project Type:** Serverless Data Pipeline  
**Submission Date:** February 12, 2026

---

## Executive Summary
This project implements a scalable, event-driven solution for automating the extraction of structured data from unstructured PDF resumes. By synthesizing **AWS Textract (Machine Learning)**, **AWS Lambda (Compute)**, and **Amazon SQS/SNS (Messaging)**, the system achieves a fully decoupled architecture capable of handling burst workloads with zero manual intervention. The design prioritizes fault tolerance, cost efficiency, and security, converting static documents into queryable analytics-ready datasets.

---

## 1. Business Context & Problem Statement

### 1.1 The Challenge: Inefficiency in Recruitment
Modern recruitment involves processing thousands of resumes weekly. Traditional manual workflows suffer from:
1.  **Latency**: Manual data entry introduces a lag of 5-10 minutes per document.
2.  **Inconsistency**: Human transcription is prone to error.
3.  **Data Opacity**: PDFs are "dark data"—unstructured and unsearchable.

### 1.2 The Solution: Automated Serverless Intelligence
This solution automates the ingestion-to-insight pipeline, delivering:
-   **Structured Output**: Converting PDFs to standardized CSV records.
-   **Elastic Scalability**: Handling 10,000+ uploads during peak recruitment drives.
-   **Operational Excellence**: Zero server management overhead.

---

## 2. Architecture Design

### 2.1 High-Level Data Flow
The system employs a **Decoupled Asynchronous Pattern** to ensure resilience:

1.  **Ingestion**: User uploads PDF to S3 (`incoming/`).
2.  **Trigger**: S3 Event notifies `SubmissionLambda`.
3.  **Async Integration**: Lambda calls `StartDocumentAnalysis` (Textract) and terminates.
4.  **Notification**: Textract publishes completion status to **SNS**.
5.  **Buffering**: SNS pushes message to **SQS Queue**.
6.  **Processing**: `ProcessingLambda` polls SQS, retrieves results, and writes CSV to S3 (`processed/`).
7.  **Lifecycle**: Original PDF is moved to `archive/` or `error/`.

### 2.2 Key Architectural Decisions
-   **Asynchronous Textract API**: Unlike the synchronous `AnalyzeDocument` (limited to single-page, 60s timeout), the async `StartDocumentAnalysis` supports multi-page documents and long-running jobs without blocking Lambda execution, reducing compute costs by >90%.
-   **SQS Buffering**: The queue acts as a "shock absorber." If 5,000 resumes are uploaded instantly, SQS queues the notifications, allowing the `ProcessingLambda` to consume them at a controlled rate, preventing downstream throttling.
-   **Dead Letter Queue (DLQ)**: Configured to capture messages that fail processing 3 times. This ensures zero data loss for "poison pill" documents.

---

## 3. Automation Logic & Implementation

### 3.1 Submission Workflow (`SubmissionLambda`)
Responsibility: **Initiation**
1.  **Trigger**: S3 `ObjectCreated` event.
2.  **Action**: Calls `textract.start_document_analysis()` with `NotificationChannel` configured to the SNS Topic.
3.  **Idempotency**: Logs `JobId` to CloudWatch for traceability.

### 3.2 Processing Workflow (`ProcessingLambda`)
Responsibility: **Transformation**
1.  **Trigger**: SQS Message batch.
2.  **Validation**: Checks `Status == SUCCEEDED`. If `FAILED`, moves file to `error/`.
3.  **Retrieval**: Calls `GetDocumentAnalysis(JobId)` with pagination loop (`NextToken`) to retrieve all blocks.
4.  **Intelligent Extraction**:
    -   Iterates `QUERY` blocks (e.g., "What is the Email?").
    -   Filters results with **Confidence Score < 90.0%** to ensure high data quality.
5.  **Persistence**:
    -   Writes structured CSV to `processed/`.
    -   Moves source PDF to `archive/` (Success) or `error/` (Failure).

---

## 4. Data Specification & Schema

### 4.1 Output Schema (CSV)
The system outputs a standardized UTF-8 CSV.

| Field Name | Type | Description | Null Handling |
| :--- | :--- | :--- | :--- |
| **Name** | String | Candidate's Full Name | Empty String |
| **Email** | String | Validated Email Format | Empty String |
| **Phone** | String | Contact Number | Empty String |
| **Skills** | String | Comma-separated list | Empty String |
| **University** | String | Institution Name | Empty String |
| **Degree** | String | Highest Degree | Empty String |
| **Experience** | String | Years of Experience | Empty String |

### 4.2 Aggregation Strategy
Unlike traditional databases, this "Data Lake" approach stores 1 CSV per Resume. This is optimized for **AWS Athena**, which can query thousands of small CSV files as a single virtual table using Presto SQL.

---

## 5. Cost Estimation (Monthly)

**Scenario**: Processing **10,000 Resumes** per month (avg. 1 page per document).

### 5.1 Amazon Textract (AI Service)
-   **Pricing Model**: Per Page (Queries Feature).
-   **Rate**: $15.00 per 1,000 pages (us-east-1).
-   **Calculation**: `(10,000 pages / 1,000) * $15.00` = **$150.00**

### 5.2 AWS Lambda (Compute)
-   **Allocated Memory**: 128 MB.
-   **Total Invocations**: 20,000 (10k Submission + 10k Processing).
-   **Avg Duration**: 100ms (Submission) + 2000ms (Processing).
-   **Total Compute**: ~21,000 seconds -> 2,625 GB-s.
-   **Free Tier**: Includes 400,000 GB-s/month.
-   **Cost**: **$0.00**

### 5.3 Amazon S3 (Storage & Requests)
-   **Storage**: 10,000 * 500KB = 5GB. Cost: ~$0.12.
-   **Requests**: ~50,000 PUT/COPY/GET requests. Cost: ~$0.25.
-   **Total**: **~$0.37**

### **Total Monthly Estimate: ~$150.37**
*Conclusion*: The cost is effectively linear with volume, dominated entirely by the AI service (Textract). The serverless infrastructure costs are negligible.

---

## 6. Scalability & Performance Analysis

### 6.1 Throughput Formula
Maximum theoretical throughput is derived from Lambda concurrency:
$$ Throughput = \frac{\text{Concurrent Executions} \times 1000ms}{\text{Avg Execution Time (ms)}} $$

Assuming default account limits (1,000 concurrent Lambdas) and 2-second processing time:
$$ Throughput = \frac{1000 \times 1000}{2000} = 500 \text{ resumes/sec} $$

### 6.2 Daily Capacity
Even with a conservative sustained throughput of 50 resumes/sec:
-   **Hourly**: 180,000 resumes.
-   **Daily**: > 4 Million resumes.
*Verification*: The requirement of 10,000/day is less than 1% of system capacity.

---

## 7. Security & Compliance

### 7.1 Data Protection
-   **Encryption at Rest**: S3 Buckets are configured with SSE-S3 (AES-256) server-side encryption by default.
-   **Encryption in Transit**: All API calls (Lambda, Textract, S3) occur over HTTPS/TLS 1.2+.

### 7.2 Access Control (IAM)
-   **Least Privilege**:
    -   `SubmissionLambda` can *only* write to S3 and call `StartDocumentAnalysis`.
    -   Textract Service Role can *only* publish to the specific SNS topic.
    -   Guest Users (Cognito) are restricted to `PutObject` on `incoming/` only.

### 7.3 Data Privacy (PII)
-   Resumes contain Personally Identifiable Information (PII).
-   **Recommendation**: Enable S3 Object Lock or strict retention policies in a production environment to comply with GDPR/CCPA.

---

## 8. System Limitations

1.  **OCR Integrity**: Scan quality below 150 DPI significantly degrades confidence scores.
2.  **Handwriting**: While supported, cursive handwriting often yields confidence < 90%, resulting in null fields.
3.  **Layout Dependency**: Complex multi-column layouts or graphics-heavy resumes may confuse the logical reading order, though Textract's Forms/Queries engine mitigates this better than raw OCR.

---

## 9. Appendix: Bonus Dashboard Integration

To visualize the extraction results:

1.  **Athena Setup**: Create an External Table pointing to `s3://[BucketName]/processed/`.
2.  **QuickSight**: Connect to Athena as a data source.
3.  **Analytics**: Build visualizations for "Skills Distribution" and "Education Level" with hourly SPICE refreshes.

---
*End of Submission*
