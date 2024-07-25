CREATE EXTERNAL TABLE `luffa-applogs`(
  `time` string COMMENT 'from deserializer', 
  `file_name` string COMMENT 'from deserializer', 
  `container_log_time` string COMMENT 'from deserializer', 
  `stream` string COMMENT 'from deserializer', 
  `logtag` string COMMENT 'from deserializer', 
  `log` string COMMENT 'from deserializer')
PARTITIONED BY ( 
  `namespace` string COMMENT '', 
  `application` string COMMENT '', 
  `date` string COMMENT '')
ROW FORMAT SERDE 
  'org.openx.data.jsonserde.JsonSerDe' 
WITH SERDEPROPERTIES ( 
  'paths'='container_log_time,file_name,log,logtag,stream,time') 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  's3://loghub-poc-clloggingbucket5f34e4eb-zempo7pzbbsz/LightEngine/AppLogs/'
TBLPROPERTIES (
  'CrawlerSchemaDeserializerVersion'='1.0', 
  'CrawlerSchemaSerializerVersion'='1.0', 
  'UPDATED_BY_CRAWLER'='s3-log', 
  'averageRecordSize'='379', 
  'classification'='json', 
  'compressionType'='gzip', 
  'objectCount'='23704', 
  'partition_filtering.enabled'='true', 
  'recordCount'='264827', 
  'sizeKey'='28095145', 
  'typeOfData'='file')
