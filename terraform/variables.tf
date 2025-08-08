variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "The name of the project, used as a prefix for resource names."
  type        = string
  default     = "file-converter"
}

variable "s3_bucket_name" {
  description = "The name of the S3 bucket for file uploads and conversions."
  type        = string
  default     = ""
}

variable "dynamodb_table_name" {
  description = "The name of the DynamoDB table for tracking file status."
  type        = string
  default     = "FileConversionStatus"
}

variable "sqs_queue_name" {
  description = "The name of the SQS queue for file conversion events."
  type        = string
  default     = "FileConversionQueue"
}

variable "lambda_function_name" {
  description = "The name of the Lambda function for file conversion."
  type        = string
  default     = "FileToPDFConverter"
}
