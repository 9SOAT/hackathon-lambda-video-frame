import os
import json
import boto3
import subprocess
import uuid
import zipfile
import logging
from botocore.exceptions import ClientError

# Configura logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
s3       = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns      = boto3.client('sns')

# Variáveis de ambiente (definidas pelo Terraform ou console)
INPUT_BUCKET   = os.getenv('INPUT_BUCKET')
OUTPUT_BUCKET  = os.getenv('OUTPUT_BUCKET')
DDB_TABLE      = os.getenv('DDB_TABLE')
SNS_TOPIC_ARN  = os.getenv('SNS_TOPIC_ARN')
FFMPEG_BIN = "/opt/bin/ffmpeg"


def lambda_handler(event, context):
    """
    Ingress entrypoint. Disparado pelo SQS com payload S3.
    """
    for record in event.get('Records', []):
        try:
            process_message(record)
        except Exception as e:
            logger.error(f"Erro geral no registro: {e}", exc_info=True)
            # opcional: re-raise para retry automático ou enviar para DLQ

def process_message(record):
    """
    Parseia a mensagem SQS e executa o fluxo:
     - HeadObject (validação de permissão/metadados)
     - download, extração de frames, zip, upload, persistência e notificação
    """
    # decodifica o body que vem como string JSON dentro do SQS

    
    body    = json.loads(record['body'])

    logger.info(f"Iniciando job:{body}")
    
    s3_evt  = body['Records'][0]['s3']
    bucket  = s3_evt['bucket']['name']
    key     = s3_evt['object']['key']

    job_id = str(uuid.uuid4())
    logger.info(f"[{job_id}] Iniciando job para s3://{bucket}/{key}")

    # Verifica metadados antes de baixar (HeadObject)
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response['Error']['Code']
        logger.error(f"[{job_id}] Falha ao checar objeto: {code}")
        raise

    # Download do vídeo
    local_video = download_from_s3(bucket, key, job_id)

    # Extrai frames via FFmpeg
    frames_dir = extract_frames(local_video, job_id)

    # Zip das imagens
    zip_path = create_zip(frames_dir, job_id)

    # Upload do ZIP
    s3_key_zip = f"{job_id}.zip"
    upload_to_s3(zip_path, OUTPUT_BUCKET, s3_key_zip)

    # Persistência no DynamoDB
    update_metadata(job_id, key, s3_key_zip)

    # Notificação via SNS
    publish_notification(job_id, s3_key_zip)


def download_from_s3(bucket, key, job_id):
    dest = f"/tmp/{job_id}_{os.path.basename(key)}"
    logger.info(f"[{job_id}] Baixando s3://{bucket}/{key} para {dest}")
    try:
        s3.download_file(bucket, key, dest)
    except ClientError as e:
        logger.error(f"[{job_id}] Erro no download: {e.response['Error']['Message']}")
        raise
    return dest 

def extract_frames(video_path, job_id):
    out_dir = f"/tmp/frames_{job_id}"
    os.makedirs(out_dir, exist_ok=True)

    cmd = [FFMPEG_BIN, "-i", video_path, "-vf", "fps=1", f"{out_dir}/frame_%04d.jpg"]
    
    logger.info(f"[{job_id}] Executando FFmpeg: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return out_dir

def create_zip(frames_dir, job_id):
    zip_path = f"/tmp/{job_id}.zip"
    logger.info(f"[{job_id}] Criando ZIP em {zip_path}")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for fname in os.listdir(frames_dir):
            full = os.path.join(frames_dir, fname)
            zf.write(full, arcname=fname)
    return zip_path

def upload_to_s3(file_path, bucket, key):
    logger.info(f"Upload {file_path} → s3://{bucket}/{key}")
    s3.upload_file(file_path, bucket, key)

def update_metadata(job_id, input_key, output_key):
    table = dynamodb.Table(DDB_TABLE)
    item = {
        'job_id':     job_id,
        'input_key':  input_key,
        'output_key': output_key,
        'status':     'COMPLETED'
    }
    logger.info(f"[{job_id}] Gravando metadata no DynamoDB: {item}")
    table.put_item(Item=item)

def publish_notification(job_id, zip_key):
    message = {
        'job_id':      job_id,
        'download_url': f"https://{OUTPUT_BUCKET}.s3.amazonaws.com/{zip_key}"
    }
    logger.info(f"[{job_id}] Publicando SNS: {message}")
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Job {job_id} concluído",
        Message=json.dumps(message)
    )
