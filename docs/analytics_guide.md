# Analytics & Dashboard Setup Guide

This guide details how to add a private analytics layer to the Serverless Resume Processor using **Amazon Athena** and **Amazon QuickSight**.

## Part 1: Athena Setup (Data Structuring)

**Goal**: Turn the S3 `processed/` folder into a queryable SQL database.

1.  **Open Athena Console**.
2.  **Create Database & Table**:
    -   Copy the content from `docs/athena_setup.sql`.
    -   Replace `<bucket-name>` with your actual S3 bucket name.
    -   Run the queries in the Athena Editor.
3.  **Validate**:
    -   Run: `SELECT * FROM resume_analytics_db.resumes LIMIT 5;`
    -   Ensure you see structured data (Name, Email, Skills, etc.).

**Zero-Maintenance**: Since the table points to the S3 `processed/` location, any new CSV file added by the Lambda function is *immediately* available for querying. No manual refresh needed.

## Part 2: QuickSight Dashboard (Visualization)

**Goal**: Create a private dashboard for HR insights.

### Step 1: Connect Data
1.  Open **QuickSight Console**.
2.  Go to **Datasets** -> **New Dataset**.
3.  Select **Athena** as the source.
4.  Name: `ResumeAnalytics`.
5.  Select Database: `resume_analytics_db`.
6.  Select Table: `resumes`.
7.  Select **Direct Query** (for real-time freshness) or **SPICE** (for performance/caching).

### Step 2: Build Visualizations
Create an **Analysis** from the dataset and add the following visuals:

1.  **KPI Card**:
    -   **Field**: `count(Name)`
    -   **Title**: "Total Resumes Processed"
2.  **Bar Chart (Top Skills)**:
    -   **Y-Axis**: `Skills`
    -   **X-Axis**: `count(Name)`
    -   *Note*: You may need to create a Calculated Field if skills are comma-separated strings to split/count them, or rely on primary skill grouping.
3.  **Pie Chart (Education)**:
    -   **Group/Color**: `Degree`
    -   **Value**: `count(Name)`
    -   **Title**: "Education Level Distribution"
4.  **Row-Level Table**:
    -   Add all fields to a Table visual for detailed drill-down.

### Step 3: Publish Dashboard
1.  Click **Share** -> **Publish Dashboard**.
2.  Name: `HR-Resume-Insights`.
3.  **Security**: Keep permissions restricted to your IAM User/Role. Do NOT enable "Everyone in this account" unless intended.

## Part 3: Internal Showcase UI

A minimal existing page is located at `web/index.html`. 

**Usage**:
1.  Open `web/index.html` in your local browser (or via AWS Console > S3 > Open).
2.  **Upload**: Select a PDF. It uploads directly to `incoming/`.
3.  **Process**: The backend processes it. Status updates on the page.
4.  **Analyze**: Click the "Open QuickSight Dashboard" link to view updated metrics.

## Security & Permissions

### IAM Adjustments
-   **QuickSight Role**: Must have permissions to `s3:GetObject` on the bucket and `athena:*` permissions.
-   **Showcase UI**: Example `index.html` uses `AWS SDK` directly.
    -   *Warning*: For a real internal tool, configure the **Cognito Identity Pool** to allow `s3:PutObject` on `incoming/*` only.
    -   The current Guest Role in CDK (`unauth_role`) restricts permissions to the bucket resources. Ensure it includes `s3:PutObject` for `incoming/`.

### Validation Checklist
-   [ ] Athena query returns rows.
-   [ ] QuickSight visualizes data.
-   [ ] New upload -> Lambda processes -> CSV in S3 -> QuickSight refresh shows +1 count.
-   [ ] Public access to S3 bucket is BLOCKED.

## Cost Estimation (Add-on)

**Athena**:
-   $5.00 per TB scanned.
-   Small CSVs (1KB each) -> 10,000 resumes = 10MB.
-   **Cost**: Negligible (< $0.01/month).

**QuickSight**:
-   **Standard Edition**: $9/user/month (Author).
-   **Reader (Enterprise)**: $0.30/session (capped at $5/month).
-   **Total**: ~$9 - $14 / month for minimal internal usage.

**S3**:
-   Existing storage costs apply. No extra cost for "hosting" the private HTML file.
