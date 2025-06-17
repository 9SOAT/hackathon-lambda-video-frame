import json
import logging
import os
import subprocess
import zipfile

import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

# Environment variables (set via Terraform or console)
INPUT_BUCKET = os.getenv("INPUT_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")
DDB_TABLE = os.getenv("DDB_TABLE")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
FFMPEG_BIN = "/opt/bin/ffmpeg"


def lambda_handler(event, context):
    """Ingress entrypoint. Triggered by SQS with S3 payload."""
    for record in event.get("Records", []):
        try:
            process_message(record)
        except Exception as err:
            logger.error(f"[lambda_handler] Error: {err}", exc_info=True)
            # Optional: re-raise for retry or send to DLQ


def process_message(record):
    """
    Parse SQS message and execute workflow:
    - HeadObject (permission/metadata validation)
    - download, frame extraction, zip, upload, persistence, notification
    """
    body = json.loads(record["body"])
    logger.info(f"[process_message] Payload: {body}")

    s3_event = body["Records"][0]["s3"]
    bucket_name = s3_event["bucket"]["name"]
    object_key = s3_event["object"]["key"]

    filename = os.path.basename(object_key)
    parts = filename.split(".")
    if len(parts) != 3:
        raise ValueError(f"Nome de arquivo inesperado: {filename}")
    prefix, timestamp, _ext = parts

    logger.info(f"Iniciando job para {filename} → pasta '{prefix}', arquivo '{timestamp}.zip'")


    # Validate metadata before download
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
    except ClientError as err:
        error_code = err.response["Error"]["Code"]
        logger.error(f"HeadObject failed: {error_code}")
        raise

    local_video = download_from_s3(bucket_name, object_key, prefix, timestamp)
    frames_dir = extract_frames(local_video, prefix, timestamp)
    zip_path = create_zip(frames_dir, prefix, timestamp)

    zip_key = f"{prefix}/{timestamp}.zip"
    upload_to_s3(zip_path, OUTPUT_BUCKET, zip_key)
    update_metadata(prefix, f"s3://{bucket_name}/{object_key}", f"s3://{OUTPUT_BUCKET}/{zip_key}")
    publish_notification(prefix, timestamp, zip_key)


def download_from_s3(bucket, key, prefix, timestamp):
    """Download file from S3 to local /tmp directory."""
    destination = f"/tmp/{prefix}_{timestamp}.mp4"
    logger.info(f"Baixando s3://{bucket}/{key} → {destination}")

    try:
        s3_client.download_file(bucket, key, destination)
    except ClientError as err:
        msg = err.response["Error"]["Message"]
        logger.error(f"Download error: {msg}")
        raise
    return destination


def extract_frames(video_path, prefix, timestamp):
    """Extract frames from video using FFmpeg."""
    out_dir = f"/tmp/frames_{prefix}_{timestamp}"
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        FFMPEG_BIN,
        "-i",
        video_path,
        "-vf",
        "fps=1",
        f"{out_dir}/frame_%04d.jpg",
    ]
    logger.info(f"Running FFmpeg: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return out_dir


def create_zip(frames_dir, prefix, timestamp):
    zip_path = f"/tmp/{prefix}_{timestamp}.zip"
    logger.info(f"Criando ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname in os.listdir(frames_dir):
            full = os.path.join(frames_dir, fname)
            zf.write(full, arcname=fname)
    return zip_path


def upload_to_s3(file_path, bucket, key):
    logger.info(f"Upload {file_path} → s3://{bucket}/{key}")
    s3_client.upload_file(file_path, bucket, key)


def update_metadata(prefix, input_key, output_key):
    table = dynamodb.Table(DDB_TABLE)
    
    item = {
        "user_prefix": prefix,
        "timestamp": generate_timestamp(),
        "input_key": input_key,
        "output_key": output_key,
        "status": "COMPLETED",
    }
    logger.info(f"Gravando metadata: {item}")
    table.put_item(Item=item)


def publish_notification(prefix, timestamp, zip_key):
    url = f"https://{OUTPUT_BUCKET}.s3.amazonaws.com/{zip_key}"
    message = {"user_prefix": prefix, "timestamp": timestamp, "download_url": url}
    logger.info(f"Publicando SNS: {message}")
    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[{prefix}] Arquivo {timestamp}.zip pronto",
        Message=json.dumps(message),
    )

def generate_timestamp() -> str:
    """
    Gera um timestamp string no formato YYYYMMDDHHMMSS.
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")