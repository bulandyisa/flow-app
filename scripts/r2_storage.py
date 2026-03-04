"""Cloudflare R2 storage module for flow-automation.

Provides S3-compatible access to R2 for both the bot (flow_bot_v2.py)
and the dashboard (dashboard.py). Falls back gracefully when R2 is not configured.

Required env vars: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL
"""

import json
import os
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

# Config from environment
_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID', '')
_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY_ID', '')
_SECRET_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
_BUCKET = os.environ.get('R2_BUCKET', 'flow-automation')
_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', '').rstrip('/')

_client = None


def is_configured() -> bool:
    """Check if R2 credentials are available."""
    return bool(HAS_BOTO3 and _ACCOUNT_ID and _ACCESS_KEY and _SECRET_KEY)


def get_client():
    """Get or create S3 client for R2."""
    global _client
    if _client is None:
        if not is_configured():
            return None
        _client = boto3.client(
            's3',
            endpoint_url=f'https://{_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=_ACCESS_KEY,
            aws_secret_access_key=_SECRET_KEY,
            config=Config(retries={'max_attempts': 3, 'mode': 'adaptive'}),
            region_name='auto',
        )
    return _client


def upload_file(local_path, r2_key: str) -> bool:
    """Upload a local file to R2. Returns True on success."""
    client = get_client()
    if not client:
        return False
    local_path = Path(local_path)
    if not local_path.exists():
        return False
    content_type = 'application/json' if local_path.suffix == '.json' else \
                   'image/png' if local_path.suffix == '.png' else \
                   'image/jpeg' if local_path.suffix in ('.jpg', '.jpeg') else \
                   'video/mp4' if local_path.suffix == '.mp4' else \
                   'application/octet-stream'
    try:
        client.upload_file(str(local_path), _BUCKET, r2_key, ExtraArgs={'ContentType': content_type})
        return True
    except ClientError as e:
        print(f'  R2 upload error ({r2_key}): {e}')
        return False


def upload_bytes(data: bytes, r2_key: str, content_type: str = 'application/octet-stream') -> bool:
    """Upload bytes directly to R2."""
    client = get_client()
    if not client:
        return False
    try:
        client.put_object(Bucket=_BUCKET, Key=r2_key, Body=data, ContentType=content_type)
        return True
    except ClientError as e:
        print(f'  R2 upload error ({r2_key}): {e}')
        return False


def download_file(r2_key: str, local_path) -> bool:
    """Download a file from R2 to local path. Returns True on success."""
    client = get_client()
    if not client:
        return False
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        client.download_file(_BUCKET, r2_key, str(local_path))
        return True
    except ClientError:
        return False


def read_json(r2_key: str) -> dict | None:
    """Read a JSON file from R2. Returns None if not found."""
    client = get_client()
    if not client:
        return None
    try:
        resp = client.get_object(Bucket=_BUCKET, Key=r2_key)
        return json.loads(resp['Body'].read())
    except ClientError:
        return None


def write_json(r2_key: str, data: dict) -> bool:
    """Write a JSON object to R2."""
    return upload_bytes(
        json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'),
        r2_key,
        content_type='application/json',
    )


def file_exists(r2_key: str) -> bool:
    """Check if a file exists in R2 via HEAD request."""
    client = get_client()
    if not client:
        return False
    try:
        client.head_object(Bucket=_BUCKET, Key=r2_key)
        return True
    except ClientError:
        return False


def public_url(r2_key: str) -> str:
    """Get the public URL for an R2 object."""
    if _PUBLIC_URL:
        return f'{_PUBLIC_URL}/{r2_key}'
    return ''


def copy_object(src_key: str, dest_key: str) -> bool:
    """Copy an object within the same R2 bucket."""
    client = get_client()
    if not client:
        return False
    try:
        client.copy_object(Bucket=_BUCKET, Key=dest_key, CopySource={'Bucket': _BUCKET, 'Key': src_key})
        return True
    except ClientError as e:
        print(f'  R2 copy error ({src_key} → {dest_key}): {e}')
        return False


def list_prefix(prefix: str) -> list[str]:
    """List all object keys under a prefix."""
    client = get_client()
    if not client:
        return []
    keys = []
    try:
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                keys.append(obj['Key'])
    except ClientError:
        pass
    return keys
