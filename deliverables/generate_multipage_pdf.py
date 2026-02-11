from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Cloud Computing & Distributed Systems', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

# --- 1. Solution Explanation PDF ---
pdf = PDF()
pdf.add_page()
pdf.set_title("Result Explanation")
pdf.set_author("Student")

# Title Page
pdf.set_font('Arial', 'B', 24)
pdf.ln(50)
pdf.cell(0, 10, 'Automated PDF Processing', 0, 1, 'C')
pdf.cell(0, 10, 'Using AWS Serverless Architecture', 0, 1, 'C')
pdf.ln(20)
pdf.set_font('Arial', '', 14)
pdf.cell(0, 10, 'Introduction to Cloud Computing', 0, 1, 'C')
pdf.cell(0, 10, f'Date: {datetime.date.today()}', 0, 1, 'C')
pdf.add_page()

# Content
sections = [
    ("1. Executive Summary", 
     "This project implements a scalable, event-driven solution regarding the extraction of structured data from unstructured PDF resumes. By synthesizing AWS Textract, AWS Lambda, and Amazon SQS/SNS, the system achieves a fully decoupled architecture capable of handling burst workloads."),
    ("2. Business Problem", 
     "Recruitment processes involve processing thousands of resumes. Manual data entry introduces latency and errors. This solution automates the pipeline, converting 'dark data' (PDFs) into queryable insights."),
    ("3. Architecture Overview", 
     "The system follows a Decoupled Asynchronous Pattern:\n"
     "- Ingestion: S3 Bucket (incoming/)\n"
     "- Event Trigger: S3 Event -> SubmissionLambda\n"
     "- Async Integration: StartDocumentAnalysis (Textract) -> SNS -> SQS\n"
     "- Processing: ProcessingLambda -> S3 (processed/) + DynamoDB"),
    ("4. Key Design Decisions", 
     "- Async Textract: Selected over synchronous API to support multi-page documents and avoid Lambda timeouts.\n"
     "- SQS Buffering: Acts as a load leveler for burst traffic.\n"
     "- Dead Letter Queue: Ensures fault tolerance for failed messages."),
    ("5. Cost Analysis", 
     "Based on 10,000 pages/month:\n"
     "- Textract: $150.00 ($15 per 1k pages)\n"
     "- Lambda: ~$0.00 (Free Tier)\n"
     "- S3: ~$0.37\n"
     "Total: ~$150.37/month. Cost is dominated by AI services."),
    ("6. Scalability Analysis", 
     "Throughput T = (Concurrency * 1000) / Duration.\n"
     "With 1000 concurrent Lambdas and 2s processing time, T = 500 docs/sec.\n"
     "Daily Capacity > 4 Million documents, far exceeding the 10,000/day requirement."),
    ("7. Limitations",
     "- OCR Integrity: Dependent on scan quality (>150 DPI).\n"
     "- Handwriting: Variable confidence scores.\n"),
    ("8. Conclusion",
     "The project successfully demonstrates a cloud-native, serverless approach to document processing, achieving high scalability and cost-efficiency.")
]

for title, body in sections:
    pdf.chapter_title(title)
    pdf.chapter_body(body)

pdf.output('deliverables/solution_explanation.pdf')


# --- 2. Lambda Logic PDF ---
pdf = PDF()
pdf.add_page()

pdf.set_font('Arial', 'B', 24)
pdf.ln(20)
pdf.cell(0, 10, 'Technical Description:', 0, 1, 'C')
pdf.cell(0, 10, 'Lambda Logic & Control Flow', 0, 1, 'C')
pdf.add_page()

logic_sections = [
    ("1. Submission Lambda Flow", 
     "Trigger: S3 ObjectCreated (incoming/*.pdf)\n"
     "Steps:\n"
     "1. Parse Bucket and Key from event.\n"
     "2. Validate file extension.\n"
     "3. Call Textract.StartDocumentAnalysis(NotificationChannel=SNS).\n"
     "4. Log JobId to CloudWatch.\n"
     "5. Exit (Stateless)."),
    ("2. Processing Lambda Flow", 
     "Trigger: SQS Message (Batch)\n"
     "Steps:\n"
     "1. Parse Message Body -> SNS -> JobId & Status.\n"
     "2. If Status != SUCCEEDED -> Move to error/ -> Return.\n"
     "3. Call Textract.GetDocumentAnalysis(JobId).\n"
     "4. If NextToken exists -> Loop until all blocks retrieved.\n"
     "5. Parse Blocks -> Filter Confidence > 90% -> Extract Fields.\n"
     "6. Generate CSV -> S3 PutObject (processed/).\n"
     "7. Copy Source -> S3 (archive/).\n"
     "8. Delete Source -> S3 (incoming/)."),
    ("3. Error Handling & DLQ", 
     "- Try/Except blocks wrap all AWS SDK calls.\n"
     "- SQS Visibility Timeout ensures retries on transient failures.\n"
     "- Dead Letter Queue (DLQ) captures messages after 3 failed attempts."),
]

for title, body in logic_sections:
    pdf.chapter_title(title)
    pdf.chapter_body(body)

pdf.output('deliverables/lambda_logic_description.pdf')

print("PDFs generated successfully.")
