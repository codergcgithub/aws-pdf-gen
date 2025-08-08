from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import boto3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET", 'file-conversion-bucket')
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", 'FileConversionStatus')
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

app = FastAPI(title="File Conversion API")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "txt"}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FileStatus(BaseModel):
    file_id: str
    original_filename: str
    status: str
    converted_filename: Optional[str] = None
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

class FileStats(BaseModel):
    total_files: int
    successful_conversions: int
    failed_conversions: int
    pending_conversions: int
    last_24_hours: int

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    # Check file extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported.")

    try:
        # Upload file to S3
        s3_key = f"input/{file.filename}"
        s3.upload_fileobj(
            file.file,
            S3_BUCKET,
            s3_key
        )
        
        # Create DynamoDB entry
        file_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        dynamodb.put_item(
            TableName=DYNAMODB_TABLE,
            Item={
                'file_id': {'S': file_id},
                'original_filename': {'S': file.filename},
                'status': {'S': 'PENDING'},
                'created_at': {'S': datetime.now().isoformat()},
                'updated_at': {'S': datetime.now().isoformat()}
            }
        )
        
        return {"file_id": file_id, "status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{file_id}", response_model=FileStatus)
async def get_file_status(file_id: str):
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    try:
        response = dynamodb.get_item(
            TableName=DYNAMODB_TABLE,
            Key={'file_id': {'S': file_id}}
        )
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="File not found")
            
        item = response['Item']
        return FileStatus(
            file_id=item['file_id']['S'],
            original_filename=item['original_filename']['S'],
            status=item['status']['S'],
            converted_filename=item.get('converted_filename', {}).get('S'),
            created_at=item['created_at']['S'],
            updated_at=item['updated_at']['S'],
            error_message=item.get('error_message', {}).get('S')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/", response_model=FileStats)
async def get_file_statistics():
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    try:
        # Query DynamoDB for statistics
        response = dynamodb.scan(
            TableName=DYNAMODB_TABLE,
            ProjectionExpression="status, created_at"
        )
        
        items = response.get('Items', [])
        
        # Calculate statistics
        stats = {
            'total_files': len(items),
            'successful_conversions': sum(1 for item in items if item['status']['S'] == 'SUCCESS'),
            'failed_conversions': sum(1 for item in items if item['status']['S'] == 'FAILED'),
            'pending_conversions': sum(1 for item in items if item['status']['S'] == 'PENDING'),
            'last_24_hours': sum(
                1 for item in items 
                if datetime.fromisoformat(item['created_at']['S']) > datetime.now() - timedelta(hours=24)
            )
        }
        
        return FileStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
