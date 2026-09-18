"""
S3-compatible storage (Garage, MinIO…). boto3 is synchronous, so every call
goes through `asyncio.to_thread`.
"""
import asyncio

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

from src.domain.ports.storage import RawStoragePort


class GarageS3Storage(RawStoragePort):
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    async def put(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        logger.debug("storage.put key={} bytes={}", key, len(body))
        return key

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=self._bucket, Key=key
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"404", "NoSuchKey"}:
                return False
            raise
        return True
