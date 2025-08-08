import boto3
import os
import tempfile
from PIL import Image
import subprocess
import logging
from datetime import datetime

S3_BUCKET = os.getenv('S3_BUCKET')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE')
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def update_dynamodb_status(file_id, status, error_message=None):
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    try:
        dynamodb.update_item(
            TableName=DYNAMODB_TABLE,
            Key={'file_id': {'S': file_id}},
            UpdateExpression='SET #status = :status, updated_at = :updated_at, error_message = :error_message',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': {'S': status},
                ':updated_at': {'S': datetime.now().isoformat()},
                ':error_message': {'S': error_message} if error_message else {'NULL': True}
            }
        )
    except Exception as e:
        logger.error(f"Error updating DynamoDB: {str(e)}")
        raise

def convert_document_to_pdf(bucket, key, file_id):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    try:
        _, input_ext = os.path.splitext(key)
        input_ext = input_ext.lower()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_input_path = os.path.join(tmpdir, os.path.basename(key))
            local_output_path = os.path.join(tmpdir, f"{file_id}.pdf")

            s3.download_file(bucket, key, local_input_path)

            subprocess.run(
                ["/opt/bin/unoconv", "-f", "pdf", "-o", local_output_path, local_input_path],
                check=True
            )
            s3.upload_file(local_output_path, bucket, f"output/{file_id}.pdf")
            return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting document to PDF: {e}")
        return False
    except Exception as e:
        logger.error(f"Error converting document to PDF: {str(e)}")
        return False

def convert_image_to_pdf(bucket, key, file_id):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    try:
        _, input_ext = os.path.splitext(key)
        input_ext = input_ext.lower()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_input_path = os.path.join(tmpdir, os.path.basename(key))
            local_output_path = os.path.join(tmpdir, f"{file_id}.pdf")

            s3.download_file(bucket, key, local_input_path)

            image = Image.open(local_input_path)
            image.save(local_output_path, "PDF", resolution=100.0)
            s3.upload_file(local_output_path, bucket, f"output/{file_id}.pdf")
            return True
    except Exception as e:
        logger.error(f"Error converting image to PDF: {str(e)}")
        return False

def lambda_handler(event, context):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    for record in event['Records']:
        try:
            bucket_name = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            file_id = os.path.splitext(os.path.basename(key))[0]

            update_dynamodb_status(file_id, 'PROCESSING')

            _, input_ext = os.path.splitext(key)
            input_ext = input_ext.lower()

            success = False
            if input_ext in ['.jpg', '.jpeg', '.png']:
                success = convert_image_to_pdf(bucket_name, key, file_id)
            elif input_ext in ['.doc', '.docx', '.xls', '.xlsx', '.txt']:
                success = convert_document_to_pdf(bucket_name, key, file_id)
            else:
                raise ValueError(f"Unsupported file type: {input_ext}")

            if success:
                update_dynamodb_status(file_id, 'SUCCESS')
            else:
                raise Exception("Conversion failed")

        except Exception as e:
            logger.error(f"Error processing record: {record}. Error: {e}")
            # Attempt to get file_id for status update, may not be available
            try:
                key = record['s3']['object']['key']
                file_id = os.path.splitext(os.path.basename(key))[0]
                update_dynamodb_status(file_id, 'FAILED', error_message=str(e))
            except Exception as inner_e:
                logger.error(f"Could not update status. Record may be malformed. Error: {inner_e}")

    return {'statusCode': 200, 'body': 'Processing complete'}
