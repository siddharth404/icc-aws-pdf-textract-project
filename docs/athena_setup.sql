-- Part 1: Create Database
CREATE DATABASE IF NOT EXISTS resume_analytics_db;

-- Part 2: Create External Table
-- Replace <bucket-name> with your actual S3 bucket name
CREATE EXTERNAL TABLE IF NOT EXISTS resume_analytics_db.resumes (
  `Name` STRING,
  `Email` STRING,
  `Phone` STRING,
  `Skills` STRING,
  `University` STRING,
  `Degree` STRING,
  `Experience` STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
ESCAPED BY '\\'
LINES TERMINATED BY '\n'
LOCATION 's3://<bucket-name>/processed/'
TBLPROPERTIES (
  'skip.header.line.count'='1',
  'serialization.null.format'=''
);

-- Part 3: Validation Query
SELECT * FROM resume_analytics_db.resumes LIMIT 10;
