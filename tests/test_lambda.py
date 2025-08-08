import pytest
from moto import mock_s3, mock_dynamodb
import boto3
import os
from lambda_app.convert_to_pdf import lambda_handler
from unittest.mock import patch

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["DYNAMODB_TABLE"] = "test-table"

@pytest.fixture
@mock_s3
def s3_bucket(aws_credentials):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")
    yield

@pytest.fixture
@mock_dynamodb
def dynamodb_table(aws_credentials):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table",
        KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}
    )
    yield

def create_s3_event(bucket, key):
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key}
                }
            }
        ]
    }

def test_lambda_handler_image(s3_bucket, dynamodb_table):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="test-bucket", Key="input/test.png", Body=b'imagedata')
    event = create_s3_event("test-bucket", "input/test.png")

    # Mock image conversion to avoid PIL dependency in test environment
    with patch('lambda_app.convert_to_pdf.convert_image_to_pdf', return_value=True) as mock_convert:
        result = lambda_handler(event, None)
        mock_convert.assert_called_once_with("test-bucket", "input/test.png", "test")

    assert result['statusCode'] == 200

@patch('subprocess.run')
def test_lambda_handler_document(mock_run, s3_bucket, dynamodb_table):
    mock_run.return_value = None # Mock successful subprocess call
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="test-bucket", Key="input/test.docx", Body=b'docdata')
    event = create_s3_event("test-bucket", "input/test.docx")

    result = lambda_handler(event, None)

    assert result['statusCode'] == 200

def test_lambda_handler_unsupported(s3_bucket, dynamodb_table):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="test-bucket", Key="input/test.gif", Body=b'gifdata')
    event = create_s3_event("test-bucket", "input/test.gif")

    result = lambda_handler(event, None)

    # Check that status is FAILED in DynamoDB
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    item = dynamodb.get_item(
        TableName="test-table",
        Key={'file_id': {'S': 'test'}}
    )
    assert item['Item']['status']['S'] == 'FAILED'
