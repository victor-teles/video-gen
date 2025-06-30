@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Setting up S3 bucket for Video Clip Generator...
echo ====================================

REM Check if .env file exists and load variables
if not exist "..\\.env" (
    echo ERROR: .env file not found!
    echo Please create a .env file with your AWS credentials
    pause
    exit /b 1
)

REM Load environment variables from .env
for /f "tokens=1,2 delims==" %%a in (..\\.env) do (
    set %%a=%%b
)

REM Check if AWS CLI is installed
where aws >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: AWS CLI is not installed!
    echo Please install AWS CLI from: https://aws.amazon.com/cli/
    pause
    exit /b 1
)

REM Check if required environment variables are set
if "%AWS_ACCESS_KEY_ID%"=="" (
    echo ERROR: AWS credentials not found in .env file!
    echo Please ensure you have the following in your .env file:
    echo AWS_ACCESS_KEY_ID=your_access_key
    echo AWS_SECRET_ACCESS_KEY=your_secret_key
    echo AWS_REGION=your_region
    pause
    exit /b 1
)

REM Set bucket name
if "%S3_BUCKET_NAME%"=="" (
    set "BUCKET_NAME=trod-video-clips"
) else (
    set "BUCKET_NAME=%S3_BUCKET_NAME%"
)

echo Creating S3 bucket: %BUCKET_NAME%...

REM Create S3 bucket
if "%AWS_REGION%"=="us-east-1" (
    aws s3api create-bucket --bucket "%BUCKET_NAME%" --region "%AWS_REGION%"
) else (
    aws s3api create-bucket --bucket "%BUCKET_NAME%" --region "%AWS_REGION%" --create-bucket-configuration LocationConstraint="%AWS_REGION%"
)

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create bucket!
    pause
    exit /b 1
)

echo Enabling versioning...
aws s3api put-bucket-versioning --bucket "%BUCKET_NAME%" --versioning-configuration Status=Enabled

echo Setting up CORS policy...
(
    echo {
    echo     "CORSRules": [
    echo         {
    echo             "AllowedHeaders": ["*"],
    echo             "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    echo             "AllowedOrigins": ["https://trod.ai", "https://api.trod.ai", "http://localhost:3000", "http://localhost:8000"],
    echo             "ExposeHeaders": ["ETag", "x-amz-server-side-encryption"],
    echo             "MaxAgeSeconds": 3000
    echo         }
    echo     ]
    echo }
) > cors.json

aws s3api put-bucket-cors --bucket "%BUCKET_NAME%" --cors-configuration file://cors.json

echo Creating bucket structure...
echo. > temp_file
aws s3 cp temp_file "s3://%BUCKET_NAME%/uploads/.keep"
aws s3 cp temp_file "s3://%BUCKET_NAME%/processing/.keep"
aws s3 cp temp_file "s3://%BUCKET_NAME%/results/.keep"
del temp_file

echo Setting up lifecycle policies...
(
    echo {
    echo     "Rules": [
    echo         {
    echo             "ID": "CleanupRule",
    echo             "Status": "Enabled",
    echo             "Filter": {
    echo                 "Prefix": "uploads/"
    echo             },
    echo             "Expiration": {
    echo                 "Days": 1
    echo             }
    echo         },
    echo         {
    echo             "ID": "ProcessingCleanup",
    echo             "Status": "Enabled",
    echo             "Filter": {
    echo                 "Prefix": "processing/"
    echo             },
    echo             "Expiration": {
    echo                 "Days": 1
    echo             }
    echo         },
    echo         {
    echo             "ID": "ResultsCleanup",
    echo             "Status": "Enabled",
    echo             "Filter": {
    echo                 "Prefix": "results/"
    echo             },
    echo             "Expiration": {
    echo                 "Days": 7
    echo             }
    echo         }
    echo     ]
    echo }
) > lifecycle.json

aws s3api put-bucket-lifecycle-configuration --bucket "%BUCKET_NAME%" --lifecycle-configuration file://lifecycle.json

REM Clean up temporary files
del cors.json lifecycle.json

echo ====================================
echo S3 bucket setup complete!
echo ====================================
echo Bucket structure:
echo   s3://%BUCKET_NAME%/
echo   - uploads/     (temporary storage for uploaded videos)
echo   - processing/  (temporary storage for videos being processed)
echo   - results/     (storage for generated clips and captions)
echo.
echo Lifecycle policies:
echo   - uploads/: deleted after 1 day
echo   - processing/: deleted after 1 day
echo   - results/: deleted after 7 days
echo ====================================

pause 