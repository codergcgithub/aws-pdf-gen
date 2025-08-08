import pytest
from fastapi.testclient import TestClient
from moto import mock_s3, mock_dynamodb
import boto3
import os

# Set environment variables for testing
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['DYNAMODB_TABLE'] = 'test-table'

from main import app

client = TestClient(app)

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"

@pytest.fixture
@mock_s3
def s3_bucket(aws_credentials):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=os.environ['S3_BUCKET'])
    yield

@pytest.fixture
@mock_dynamodb
def dynamodb_table(aws_credentials):
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName=os.environ['DYNAMODB_TABLE'],
        KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}
    )
    yield

def test_upload_file_success(s3_bucket, dynamodb_table):
    with open("test.txt", "w") as f:
        f.write("hello world")
    
    with open("test.txt", "rb") as f:
        response = client.post("/upload/", files={"file": ("test.txt", f, "text/plain")})
    
    assert response.status_code == 200
    assert "file_id" in response.json()

    os.remove("test.txt")

def test_upload_file_unsupported_type():
    with open("test.gif", "w") as f:
        f.write("gif content")

    with open("test.gif", "rb") as f:
        response = client.post("/upload/", files={"file": ("test.gif", f, "image/gif")})

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]

    os.remove("test.gif")

def test_get_file_status(s3_bucket, dynamodb_table):
    # Setup a dummy item in DynamoDB
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    file_id = "20250101120000_test.txt"
    dynamodb.put_item(
        TableName=os.environ['DYNAMODB_TABLE'],
        Item={
            'file_id': {'S': file_id},
            'original_filename': {'S': 'test.txt'},
            'status': {'S': 'SUCCESS'},
            'created_at': {'S': '2025-01-01T12:00:00'},
            'updated_at': {'S': '2025-01-01T12:01:00'},
            'converted_filename': {'S': 'output/20250101120000_test.pdf'}
        }
    )

    response = client.get(f"/status/{file_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['file_id'] == file_id
    assert data['status'] == 'SUCCESS'

def test_get_file_statistics(s3_bucket, dynamodb_table):
    # Setup dummy items
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    items = [
        {'file_id': {'S': '1'}, 'status': {'S': 'SUCCESS'}, 'created_at': {'S': '2025-01-01T10:00:00'}},
        {'file_id': {'S': '2'}, 'status': {'S': 'FAILED'}, 'created_at': {'S': '2025-01-01T11:00:00'}},
        {'file_id': {'S': '3'}, 'status': {'S': 'PENDING'}, 'created_at': {'S': '2025-01-01T12:00:00'}},
        {'file_id': {'S': '4'}, 'status': {'S': 'SUCCESS'}, 'created_at': {'S': '2025-01-01T13:00:00'}},
    ]
    for item in items:
        dynamodb.put_item(TableName=os.environ['DYNAMODB_TABLE'], Item=item)

    response = client.get("/stats/")

    assert response.status_code == 200
    stats = response.json()
    assert stats['total_files'] == 4
    assert stats['successful_conversions'] == 2
    assert stats['failed_conversions'] == 1
    assert stats['pending_conversions'] == 1
