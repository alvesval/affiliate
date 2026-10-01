from __future__ import annotations
import io
import re
import uuid
import boto3
from botocore.config import Config
from app.core.config import settings

class MediaStorageError(RuntimeError):
    pass

def _client():
    missing=[name for name,value in {
        'R2_ENDPOINT_URL':settings.r2_endpoint_url,
        'R2_ACCESS_KEY_ID':settings.r2_access_key_id,
        'R2_SECRET_ACCESS_KEY':settings.r2_secret_access_key,
        'R2_BUCKET_NAME':settings.r2_bucket_name,
    }.items() if not value]
    if missing:
        raise MediaStorageError('Storage de mídia não configurado. Configure: '+', '.join(missing))
    return boto3.client('s3',endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,aws_secret_access_key=settings.r2_secret_access_key,
        region_name='auto',config=Config(signature_version='s3v4'))

def build_key(variant_id:int, filename:str)->str:
    safe=re.sub(r'[^A-Za-z0-9._-]+','-',filename or 'video.mp4').strip('-') or 'video.mp4'
    return f'content/variants/{variant_id}/{uuid.uuid4().hex}-{safe}'

def put_bytes(key:str, data:bytes, content_type:str)->None:
    try:
        _client().put_object(Bucket=settings.r2_bucket_name,Key=key,Body=data,ContentType=content_type)
    except Exception as exc:
        raise MediaStorageError(f'Falha ao armazenar mídia: {exc}') from exc

def get_bytes(key:str)->bytes:
    try:
        obj=_client().get_object(Bucket=settings.r2_bucket_name,Key=key)
        return obj['Body'].read()
    except Exception as exc:
        raise MediaStorageError(f'Falha ao ler mídia armazenada: {exc}') from exc

def delete(key:str)->None:
    if not key:return
    try:_client().delete_object(Bucket=settings.r2_bucket_name,Key=key)
    except Exception:pass
