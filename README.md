# AWS File to PDF Converter

A distributed AWS application that converts files to PDF format using S3, SQS, Lambda, and DynamoDB.

## Architecture

The system consists of the following AWS components:

1. **S3 Bucket**
   - Input bucket for uploaded files
   - Output bucket for converted PDFs

2. **SQS Queue**
   - Manages file conversion requests
   - Ensures reliable processing of conversion tasks

3. **Lambda Function**
   - Processes file conversion requests
   - Converts files to PDF format
   - Updates DynamoDB with status

4. **DynamoDB**
   - Stores file conversion status and metadata
   - Maintains conversion statistics

5. **FastAPI Backend**
   - RESTful API for file upload and status checking
   - Provides conversion statistics

## Setup

### Prerequisites
- AWS account with necessary permissions
- Python 3.8+
- Docker (for local development)

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your AWS credentials:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
DYNAMODB_TABLE=FileConversionStatus
S3_BUCKET=file-conversion-bucket
```

3. Run the FastAPI server:
```bash
uvicorn main:app --reload
```

### Deployment

1. **Build the Lambda Package**

   Before deploying with Terraform, you must build the Lambda deployment package, which includes the function's Python dependencies.

   ```bash
   chmod +x scripts/build_lambda.sh
   ./scripts/build_lambda.sh
   ```

2. **Deploy with Terraform**

   Navigate to the `terraform` directory and initialize Terraform:

   ```bash
   cd terraform
   terraform init
   ```

   Review the execution plan:

   ```bash
   terraform plan
   ```

   Apply the configuration to create the AWS resources:

   ```bash
   terraform apply
   ```

   Terraform will provision all the necessary resources, including S3, DynamoDB, SQS, and the Lambda function with the correct code and dependencies.

## API Endpoints

### Upload File
```
POST /upload/
```
Upload a file for conversion

### Get File Status
```
GET /status/{file_id}
```
Check the status of a specific file conversion

### Get Statistics
```
GET /stats/
```
Get overall conversion statistics

## File Conversion Process

1. User uploads a file through the FastAPI endpoint
2. File is stored in S3 input bucket
3. S3 event triggers SQS queue
4. Lambda function processes the file
5. Converted PDF is stored in S3 output bucket
6. Status updates are recorded in DynamoDB

## Error Handling

The system includes comprehensive error handling:
- File upload validation
- Conversion process monitoring
- Detailed error messages in DynamoDB
- Retry mechanisms for failed conversions

## Monitoring

The application provides:
- Real-time conversion status
- Conversion statistics
- Error tracking
- Performance metrics

## Security

- All AWS resources are secured with IAM roles and policies
- S3 buckets have proper access controls
- Environment variables are used for sensitive data
- HTTPS is enforced for API endpoints
