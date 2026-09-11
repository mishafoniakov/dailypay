"""Основа извлечения файлов из S3-совместимого хранилища (MinIO).

Читает объекты из бакета и кладёт их в локальный landing (`/data/raw/{ds}/`).
Подключение задаётся переменными окружения, значения по умолчанию — локальный MinIO.
"""

from __future__ import annotations

import os
from pathlib import Path


def _s3_settings() -> dict:
    return {
        "endpoint_url": os.environ.get("S3_ENDPOINT", "http://minio:9000"),
        "aws_access_key_id": os.environ.get(
            "S3_ACCESS_KEY", os.environ.get("AWS_ACCESS_KEY_ID", "dailypayadmin")
        ),
        "aws_secret_access_key": os.environ.get(
            "S3_SECRET_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "dailypayadmin")
        ),
        "region_name": os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        "bucket": os.environ.get("S3_BUCKET", "dailypay-raw"),
        "prefix": os.environ.get("S3_PREFIX", ""),
        "dest_root": os.environ.get("S3_LANDING_DIR", "/data/raw"),
    }


def _client(settings: dict):
    try:
        import boto3
        from botocore.client import Config
    except ImportError as exc:
        raise ImportError(
            "Для извлечения из S3 нужен boto3. Добавьте его в airflow/requirements.txt "
            "и установите в образе Airflow."
        ) from exc

    return boto3.client(
        "s3",
        endpoint_url=settings["endpoint_url"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"],
        region_name=settings["region_name"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _ensure_bucket(client, bucket: str) -> None:
    from botocore.exceptions import ClientError

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def extract_from_s3(
    *,
    logical_date: str,
    bucket: str | None = None,
    prefix: str | None = None,
    dest_root: str | None = None,
) -> dict:
    """Скачать объекты из бакета в landing-директорию за дату `logical_date`."""
    settings = _s3_settings()
    bucket = bucket or settings["bucket"]
    prefix = settings["prefix"] if prefix is None else prefix
    dest_root = dest_root or settings["dest_root"]
    dest_dir = Path(dest_root) / logical_date
    dest_dir.mkdir(parents=True, exist_ok=True)

    client = _client(settings)
    _ensure_bucket(client, bucket)

    downloaded: list[dict] = []
    paginator = client.get_paginator("list_objects_v2")
    list_kwargs: dict = {"Bucket": bucket}
    if prefix:
        list_kwargs["Prefix"] = prefix

    for page in paginator.paginate(**list_kwargs):
        for obj in page.get("Contents") or []:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            local_path = dest_dir / key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(local_path))
            downloaded.append(
                {
                    "key": key,
                    "path": str(local_path),
                    "size": int(obj.get("Size") or 0),
                }
            )

    return {
        "source": "s3",
        "bucket": bucket,
        "prefix": prefix,
        "endpoint": settings["endpoint_url"],
        "landing": str(dest_dir),
        "files": downloaded,
        "rows": len(downloaded),
        "ds": logical_date,
    }
