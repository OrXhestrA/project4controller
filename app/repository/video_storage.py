import os
import shutil
from datetime import datetime

import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from app.config.base_config import settings
from app.models.domain import VideoDataDB
from app.utils.logger import log
from app.config import database_config
from app.repository.cache_aside_storage import CacheAsideRepository

class VideoStorage:
    """
    Video Storage Interface
    """

    def __init__(self):
        self.mode = settings.STORAGE_MODE
        self.local_path = Path(settings.LOCAL_STORAGE_PATH)
        self.local_path.mkdir(parents=True, exist_ok=True)

        if self.mode == "s3":
            try:
                self.s3_client = database_config.get_s3_client()
            except Exception as e:
                log.error(f"Failed to connect to S3: {e}")
                self.s3_client = None
        else:
            self.s3_client = None

    async def save_frame(
            self,
            file: UploadFile,
            user_id: str,
            timestamp: datetime,
            video_format: str = "jpg",
            repo: CacheAsideRepository = None
    ) -> dict:
        """
        保存视频帧
        :param repo:
        :param timestamp:
        :param file:
        :param user_id:
        :param video_format:
        :return: {
            "s3_path": "",
            "local_path": "",
        }
        """
        storage_path = f"video_{user_id}_{timestamp.strftime('%Y%m%d%H%M%S')}.{video_format}"

        result = {
            "s3_path": None,
            "local_path": None
        }
        log.info(f"start save frames, save mode : {self.mode}")
        if self.mode == "local":
            result["local_path"] = await self.save_frame_local(storage_path, file)

        elif self.mode == "s3" and self.s3_client:
            try:
                self.s3_client.upload_fileobj(
                    file.file,
                    settings.S3_BUCKET_NAME,
                    storage_path
                )
                result["s3_path"] = f"https://{settings.S3_BUCKET_NAME}.s3.amazonaws.com/{storage_path}"
                log.info(f"上传帧到S3: {result['s3_path']}")

            except Exception as e:
                log.error(f"Failed to upload frame to S3: {e}")
                result["local_path"] = await self.save_frame_local(storage_path, file)
                raise

        video_data = VideoDataDB(
            user_id=user_id,
            timestamp=timestamp,
            format=video_format,
            s3_path=result["s3_path"],
            local_path=result["local_path"]
        )
        await repo.insert_video_data(video_data)
        return result

    async def save_frame_local(
            self,
            storage_path: str,
            file: UploadFile
    ) -> str:
        """
        Save frame in local
        :param file:
        :param storage_path:
        :return: save path
        """
        if file:
            with open(os.path.join(self.local_path, storage_path), "wb") as f:
                f.write(file.file.read())
            log.info(f"保存帧到本地: {self.local_path}")
            return os.path.join(self.local_path, storage_path)

    async def get_frame(
            self,
            user_id: str,
            repo: CacheAsideRepository = None
    ):
        """
        GET VIDEO FRAME
        :param user_id:
        :param repo:
        :return:
        """
        try:
            log.info(f"Get frame - user {user_id}")

            video_path_list = await repo.get_video_data(user_id)
            print(video_path_list)
            video_list = []
            if self.mode == "local":
                for video_path in video_path_list:
                    async with aiofiles.open(video_path, "rb") as f:
                        video_list.append(await f.read())
            else:
                for video_path in video_path_list:
                    response = self.s3_client.get_object(
                        Bucket=settings.S3_BUCKET_NAME,
                        Key=video_path
                    )
                    video_list.append(response["Body"].read())
            return video_list
        except Exception as e:
            log.error(f"Failed to get frame: {e}")
            raise


storage = VideoStorage()
