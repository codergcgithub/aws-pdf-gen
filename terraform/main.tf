terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for file uploads and conversions
resource "aws_s3_bucket" "file_bucket" {
  bucket = var.s3_bucket_name == "" ? "${var.project_name}-${data.aws_caller_identity.current.account_id}" : var.s3_bucket_name

  tags = {
    Name = "${var.project_name}-bucket"
  }
}

# DynamoDB table for tracking file status
resource "aws_dynamodb_table" "status_table" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-dynamodb-table"
  }
}

# SQS queue for file conversion events
resource "aws_sqs_queue" "file_queue" {
  name                      = var.sqs_queue_name
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 300

  tags = {
    Name = "${var.project_name}-sqs-queue"
  }
}

# IAM Role for Lambda function
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda function
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "IAM policy for Lambda to access S3, SQS, and DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Effect   = "Allow",
        Resource = "${aws_s3_bucket.file_bucket.arn}/*"
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan"
        ],
        Effect   = "Allow",
        Resource = aws_dynamodb_table.status_table.arn
      },
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Effect   = "Allow",
        Resource = aws_sqs_queue.file_queue.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# S3 bucket notification to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.file_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.file_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "input/"
  }

  depends_on = [aws_sqs_queue_policy.allow_s3_to_send_messages]
}

# SQS Queue Policy to allow S3 to send messages
resource "aws_sqs_queue_policy" "allow_s3_to_send_messages" {
  queue_url = aws_sqs_queue.file_queue.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action    = "sqs:SendMessage",
        Resource  = aws_sqs_queue.file_queue.arn,
        Condition = {
          ArnEquals = { "aws:SourceArn" = aws_s3_bucket.file_bucket.arn }
        }
      }
    ]
  })
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Package the Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/../dist/convert_to_pdf.zip"
}

# Lambda function for file conversion
resource "aws_lambda_function" "file_converter" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "convert_to_pdf.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.status_table.name
      S3_BUCKET      = aws_s3_bucket.file_bucket.bucket
    }
  }

  tags = {
    Name = "${var.project_name}-lambda-function"
  }
}

# Event source mapping between SQS and Lambda
resource "aws_lambda_event_source_mapping" "sqs_lambda_mapping" {
  event_source_arn = aws_sqs_queue.file_queue.arn
  function_name    = aws_lambda_function.file_converter.arn
  batch_size       = 1
}

