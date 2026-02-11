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
LOCATION 's3://resumeprocessorworkflow-resumebucketd07ccf44-lg7bicei4qhh/processed/'
TBLPROPERTIES (
  'skip.header.line.count'='1'
);
