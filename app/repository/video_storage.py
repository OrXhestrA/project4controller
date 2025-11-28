import os
import shutil

import aiofiles
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime
from fastapi import UploadFile
from app.config.base_config import settings
from app.utils.logger import log

try:
    import boto3
    from botocore.exceptions import ClientError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    log.warning("boto3 is not installed. Please install it to use S3.")


class VideoStorage:
    """
    Video Storage Interface
    """

    def __init__(self):
        self.mode = settings.STORAGE_MODE
        self.local_path = Path(settings.LOCAL_STORAGE_PATH)
        self.cache_path = Path(settings.CACHE_PATH)

        self.local_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)

        if self.mode in ["s3", "minio"] and S3_AVAILABLE:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL if settings.S3_ENDPOINT else None,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                use_ssl=settings.USE_SSL,
            )
            self._ensure_bucket_exists()
        else:
            self.s3_client = None

    def _ensure_bucket_exists(self):
        """
        确保S3 Bucket存在，不存在则尝试创建
        :return: None
        """
        try:
            self.s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
            log.info(f"Bucket {settings.S3_BUCKET_NAME} exists")
        except ClientError as e:
            try:
                self.s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                log.info(f"Bucket {settings.S3_BUCKET_NAME} created")
            except ClientError as e:
                log.error(f"Error creating S3 bucket : {e}")

    def generate_storage_path(
            self,
            user_id: str,
            session_id: str,
            frame_id: int,
            format: str = "jpg"
    ) -> str:
        return f"videos/{user_id}/{session_id}/frame_{frame_id:06d}.{format}"

    async def save_frame(
            self,
            file: UploadFile,
            user_id: str,
            session_id: str,
            frame_id: int,
            format: str = "jpg"
    ) -> dict:
        """
        保存视频帧
        :param file:
        :param user_id:
        :param session_id:
        :param frame_id:
        :param format:
        :return: {
            "s3_path": "",
            "local_path": "",
            "file_size": 1
        }
        """
        storage_path = self.generate_storage_path(user_id, session_id, frame_id, format)
        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_FRAME_SIZE_MB * 1024 * 1024:
            log.error(f"文件大小超出限制: {file_size}")
            raise ValueError(f"文件大小超出限制 {settings.MAX_FRAME_SIZE_MB}MB")

        result = {
            "s3_path": storage_path,
            "local_path": None,
            "file_size": file_size
        }

        if self.mode == "local":
            local_file_path = self.local_path / storage_path
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(local_file_path, "wb") as f:
                await f.write(content)

            result["local_path"] = str(local_file_path)
            log.info(f"保存帧到 {local_file_path}")

        elif self.mode in ["s3", "minio"] and self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=storage_path,
                    Body=content,
                    ContentType=f"image/{format}"
                )
                log.info(f"保存帧到 S3: {storage_path}")

                if settings.ENABLE_LOCAL_CACHE:
                    cache_file_path = self.cache_path / storage_path
                    cache_file_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(cache_file_path, 'wb') as f:
                        await f.write(content)

                    result["local_path"] = str(cache_file_path)
            except ClientError as e:
                log.error(f"保存帧到 S3 失败: {e}")
                raise

        return result

    async def get_frame(self, storage_path: str, local_path: Optional[str] = None) -> bytes:
        """
        GET VIDEO FRAME
        :param storage_path:
        :param local_path:
        :return:
        """
        if local_path and os.path.exists(local_path):
            async with aiofiles.open(local_path, "rb") as f:
                return await f.read()

        if self.mode == "local":
            local_file_path = self.local_path / storage_path
            if local_file_path.exists():
                async with aiofiles.open(local_file_path, "rb") as f:
                    return await f.read()

        elif self.mode in ["s3", "minio"] and self.s3_client:
            try:
                response = self.s3_client.get_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=storage_path
                )
                content = response["Body"].read()

                if settings.ENABLE_LOCAL_CACHE:
                    cache_file_path = self.cache_path / storage_path
                    cache_file_path.parent.mkdir(parents=True, exist_ok=True)

                    async with aiofiles.open(cache_file_path, 'wb') as f:
                        await f.write(content)
                return content

            except ClientError as e:
                log.error(f"Failed to get frame from S3: {e}")
                raise
        raise FileNotFoundError(f"Frame not found: {storage_path}")

    async def delete_frame(self, storage_path: str, local_path: Optional[str] = None):
        """
        Delete Local File
        :param storage_path:
        :param local_path:
        :return:
        """
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

        if self.mode == "local":
            local_file_path = self.local_path / storage_path
            if local_file_path.exists():
                local_file_path.unlink()

        elif self.mode in ["s3", "minio"] and self.s3_client:
            try:
                self.s3_client.delete_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=storage_path
                )
            except Exception as e:
                log.error(f"Failed to delete frame from S3: {e}")

    async def delete_session(self, user_id: str, session_id: str):
        """
        Delete Session
        :param user_id:
        :param session_id:
        :return:
        """
        prefix = f"videos/{user_id}/{session_id}/"

        if self.mode == "local":
            session_dir = self.local_path / "videos" / user_id / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)

        elif self.mode in ["s3", "minio"] and self.s3_client:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=settings.S3_BUCKET_NAME,
                    Prefix=prefix
                )

                if "Contents" in response:
                    objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
                    self.s3_client.delete_objects(
                        Bucket=settings.S3_BUCKET_NAME,
                        Delete={"Objects": objects}
                    )
            except Exception as e:
                log.error(f"Failed to delete session from S3: {e}")
