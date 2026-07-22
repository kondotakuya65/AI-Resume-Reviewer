from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import aiofiles
import boto3
from botocore.client import BaseClient

from app.core.config import Settings, get_settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str, content_type: str) -> str:
        """Persist bytes and return a storage key."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object by storage key."""

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """Read object bytes by storage key."""


class LocalStorage(StorageBackend):
    def __init__(self, upload_dir: str) -> None:
        self.root = Path(upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, filename: str, content_type: str) -> str:
        ext = Path(filename).suffix or ""
        key = f"{uuid4().hex}{ext}"
        path = self.root / key
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return key

    async def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()

    async def read(self, key: str) -> bytes:
        path = self.root / key
        async with aiofiles.open(path, "rb") as f:
            return await f.read()


class S3Storage(StorageBackend):
    def __init__(self, settings: Settings) -> None:
        if not settings.aws_s3_bucket:
            raise ValueError("AWS_S3_BUCKET is required when STORAGE_BACKEND=s3")
        self.bucket = settings.aws_s3_bucket
        self.client: BaseClient = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )

    async def save(self, data: bytes, filename: str, content_type: str) -> str:
        ext = Path(filename).suffix or ""
        key = f"resumes/{uuid4().hex}{ext}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    async def read(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()


def get_storage(settings: Settings | None = None) -> StorageBackend:
    settings = settings or get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    return LocalStorage(settings.upload_dir)
