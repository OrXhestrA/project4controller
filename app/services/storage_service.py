from datetime import datetime
from typing import (
    List,
    Dict,
    Optional,
    Any
)
from app.models.request import *
from app.models.response import *
from app.models.dto import *
from app.models.domain import *
from app.utils.logger import log
from app.config.database_config import get_db, get_redis_pool
from app.repository.cache_aside_storage import CacheAsideRepository
from app.repository.video_storage import storage


class StorageService:
    """Data Upload & Getter"""

    @staticmethod
    async def upload_heart_data(request: HeartDataRequest) -> HeartDataResponse:
        """
        上传心率数据
        :param request: 上传心率数据请求
        :return: 上传心率数据响应
        """
        log.info(f"Upload heart data from user {request.user_id}")
        async for db_session in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db_session, redis_client)

            try:
                log.info(f"Insert heart data - user : {request.user_id}")
                await repo.insert_heart_data(data=request)
                return HeartDataResponse()
            except Exception as e:
                log.error(f"Insert heart data error - user : {request.user_id} - error : {e}")
                raise e

    @staticmethod
    async def get_heart_data(user_id: str) -> List[Any]:
        log.info(f"Get heart data from db - user_id : {user_id}")
        async for db_session in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db_session, redis_client)
            return await repo.get_latest_heart_data(user_id=user_id)

    @staticmethod
    async def upload_user_data(request: UserDataRequest) -> UserDataResponse:
        """
        上传用户数据
        :param request: 上传用户数据请求
        :return: 上传用户数据响应
        """
        log.info(f"Upload user data from user {request.user_id}")
        async for db_session in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db_session, redis_client)

            try:
                log.info(f"Insert user data - user {request.user_id}")
                await repo.insert_user_data(request=request)
                return UserDataResponse(user_data=request.data)
            except Exception as e:
                log.error(f"Insert user data error - user {request.user_id} - error : {e}")
                raise e

    @staticmethod
    async def upload_bio_data(request: BioDataRequest) -> BioDataResponse:
        """
        上传生化信息
        :param request: 上传生化信息请求
        :return: 上传生化信息响应
        """
        log.info(f"Upload bio data from user {request.user_id}")
        async for db_session in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db_session, redis_client)

            try:
                log.info(f"Insert bio data - user {request.user_id}")
                await repo.insert_bio_data(request=request)
                return BioDataResponse()
            except Exception as e:
                log.error(f"Insert bio data error - user {request.user_id} - error : {e}")
                raise e

    @staticmethod
    async def upload_video_data(request: VideoUploadRequest) -> VideoDataResponse:
        """
        上传视频信息
        :param request:
        :return:
        """
        log.info(f"Upload video data from user {request.user_id}")
        async for db_session in get_db():
            try:
                redis_client = await get_redis_pool()
                timestamp = datetime.now()
                result = await storage.save_frame(
                    file=request.file,
                    user_id=request.user_id,
                    timestamp=timestamp,
                    video_format=request.format,
                    repo=CacheAsideRepository(db_session, redis_client)
                )

                video_info_data = VideoFrameInfoDto(
                    timestamp=timestamp.isoformat(),
                    format=request.format,
                    s3_path=result.get("s3_path"),
                    local_path=result.get("local_path")
                )
                return VideoDataResponse(data=video_info_data)
            except Exception as e:
                log.error(f"Insert video data error - user {request.user_id} - error : {e}")
                raise e

    @staticmethod
    async def get_video_data(user_id: str) -> List[str]:
        """
        Get Video Data
        :param user_id:
        :return: List[image]
        """
        async for db_session in get_db():
            redis_client = await get_redis_pool()
            return await storage.get_frame(
                user_id=user_id,
                repo=CacheAsideRepository(db_session, redis_client)
            )