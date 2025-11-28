from sqlalchemy.engine.row import ROMappingKeysValuesView
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, update
from sqlalchemy.dialects.mysql import insert
from app.models.domain import (
    HeartRateDataDB,
    VideoDataDB,
    UserDataDB,
    TaskDataDB,
    BioDataDB
)
from app.models.request import (
    HeartDataRequest,
    UserDataRequest,
    VideoUploadRequest, BioDataRequest
)
from datetime import datetime, timedelta
import json
from app.utils.logger import log
from typing import (
    List,
    Any,
    Optional,
    Dict,
)
from redis import Redis


class CacheAsideRepository:
    def __init__(self, db: AsyncSession, redis_client: Redis):
        self.db_session = db
        self.redis = redis_client
        self.cache_ttl = 3600

    """心率数据"""

    async def insert_heart_data(self, data: HeartDataRequest) -> None:
        """
        存储心率数据到数据库（旁路缓存策略 | 先存数据库 后删Redis缓存）
        :param data: 心率数据
        :return: None
        """
        for heart_data in data.heart_rate:
            log.info(f"Insert heart data - user : {data.user_id}")
            db_data = HeartRateDataDB(
                user_id=data.user_id,
                timestamp=heart_data.timestamp,
                value=heart_data.value
            )
            self.db_session.add(db_data)
        await self.db_session.commit()
        cache_key = f"heart_rate:{data.user_id}:latest"

        try:
            await self.redis.delete(cache_key)
            log.info(f"Delete cache - key : {cache_key}")
        except Exception as e:
            log.error(f"Delete cache error - key : {cache_key} - error : {e}")

    async def get_latest_heart_data(
            self,
            user_id: str,
            limit: int = 300,
            ttl: int = 3600
    ) -> list[Any]:
        """
        获取最新心率数据（旁路缓存策略 | 先从Redis缓存中获取数据，如无则从数据库中获取数据并缓存）
        :param user_id: 用户ID
        :param limit: 获取数据的条数
        :param ttl: 缓存的过期时间
        :return: 最新心率数据
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user id")

        cache_key = f"heart_rate:{user_id}:latest"
        cache_data = await self.redis.get(cache_key)
        if cache_data:
            log.info(f"Get cache - key : {cache_key}")
            return json.loads(cache_data)

        log.info(f"Get heart data from db - user_id : {user_id}")
        query = select(HeartRateDataDB).where(
            HeartRateDataDB.user_id == user_id
        ).order_by(
            desc(HeartRateDataDB.timestamp)
        ).limit(limit)

        result = await self.db_session.execute(query)
        records = result.scalars().all()
        data = [record.value for record in records]
        log.info(f"Get heart data success - user_id : {user_id} - data : {data}")
        if data:
            await self.redis.set(cache_key, json.dumps(data), ex=ttl)
            log.info(f"Set cache - key : {cache_key}")

        return data

    """用户数据"""

    async def insert_user_data(self, request: UserDataRequest):
        """
        存储用户数据到数据库
        :param request:
        :return: None
        """
        log.info(f"Insert user data - user {request.user_id}")
        if not request.user_id or not isinstance(request.user_id, str):
            raise ValueError("Invalid user id")

        if request.data.tasks:
            log.info(f"Insert task data - user {request.user_id}")
            await self.insert_task_data(request)

        if not isinstance(request.data.age, int) or request.data.age < 0:
            raise ValueError("Invalid age")

        if request.data.gender not in [0, 1]:
            raise ValueError("Invalid gender")

        try:
            new_record = UserDataDB(
                user_id=request.user_id,
                age=request.data.age,
                gender=request.data.gender,
                occupation=request.data.occupation,
                other_info=request.data.other_info,
                timestamp=datetime.now()
            )
            self.db_session.add(new_record)
            await self.db_session.commit()
            await self.db_session.refresh(new_record)

            log.info(f"Insert user data success - user {request.user_id}, id {new_record.id}")

            deleted = await self.redis.delete(f"user_data:{request.user_id}:latest")
            log.info(f"Delete cache - key : {f'user_data:{request.user_id}:latest'} - deleted : {deleted}")
        except Exception as e:
            log.warning(f"Insert user data error - user {request.user_id} - error : {e}")
            await self.db_session.rollback()

    async def get_user_data(self, user_id: str):
        """
        获取用户数据
        :param user_id:
        :return:
        """
        log.info(f"Get user data - user {user_id}")
        cache_key = f"user_data:{user_id}:latest"
        cache_data = await self.redis.get(cache_key)
        if cache_data:
            log.info(f"Get cache - key : {cache_key}")
            return json.loads(cache_data)
        log.info(f"Get user data from db - user {user_id}")
        query = select(UserDataDB).where(
            UserDataDB.user_id == user_id
        ).order_by(
            desc(UserDataDB.timestamp)
        ).limit(1)
        result = await self.db_session.execute(query)
        record = result.scalars().first()
        if record:
            await self.redis.set(cache_key, json.dumps(record.values()), ex=self.cache_ttl)
            log.info(f"Set cache - key : {cache_key}")
            return record.values()
        return None

    """任务数据"""

    async def insert_task_data(self, request: UserDataRequest) -> None:
        """
        存储管制任务数据
        :param request:
        :return:
        """
        try:
            for task in request.data.tasks:
                new_record = TaskDataDB(
                    user_id=request.user_id,
                    task=task.task,
                    timestamp=datetime.now()
                )
                self.db_session.add(new_record)
                await self.db_session.flush()
            await self.db_session.commit()

            deleted = await self.redis.delete(f"task_data:{request.user_id}:latest")
            log.info(f"Delete cache - key : {f'task_data:{request.user_id}:latest'} - deleted : {deleted}")

        except Exception as e:
            log.warning(f"Insert task data error - user {request.user_id} - error : {e}")
            await self.db_session.rollback()

    async def get_task_data(self, user_id: str):
        """
        获取管制任务数据
        :param user_id:
        :return:
        """
        log.info(f"Get task data - user {user_id}")
        cache_key = f"task_data:{user_id}:latest"
        cache_data = await self.redis.get(cache_key)
        if cache_data:
            log.info(f"Get cache - key : {cache_key}")
            return json.loads(cache_data)
        log.info(f"Get task data from db - user {user_id}")
        query = select(TaskDataDB).where(
            and_(TaskDataDB.user_id == user_id,
                 TaskDataDB.timestamp >= datetime.now() - timedelta(minutes=30))
        ).order_by(
            desc(TaskDataDB.timestamp)
        )
        result = await self.db_session.execute(query)
        records = result.scalars().all()
        if records:
            data = [record.values() for record in records]
            await self.redis.set(cache_key, json.dumps(data), ex=self.cache_ttl)
            log.info(f"Set cache - key : {cache_key}")
            return data
        return None

    """视频数据"""

    # TODO
    async def insert_video_data(self, data: VideoDataDB) -> None:
        pass

    """生化数据"""
    async def insert_bio_data(self, request: BioDataRequest) -> None:
        """
        插入生化数据
        :param request:
        :return: None
        """
        try:
            for bio_data in request.data:
                new_record = BioDataDB(
                    user_id=request.user_id,
                    timestamp=datetime.now(),
                    value_1=bio_data.value_1,
                    value_2=bio_data.value_2
                )
                self.db_session.add(new_record)
            await self.db_session.commit()

            deleted = await self.redis.delete(f"bio_data:{request.user_id}:latest")
            log.info(f"Delete cache - key : {f'bio_data:{request.user_id}:latest'} - deleted : {deleted}")

        except Exception as e:
            log.warning(f"Insert bio data error - user {request.user_id} - error : {e}")
            await self.db_session.rollback()

    async def get_bio_data(self, user_id: str):
        """
        获取生化数据
        :param user_id:
        :return:
        """
        log.info(f"Get bio data - user {user_id}")
        cache_key = f"bio_data:{user_id}:latest"
        cache_data = await self.redis.get(cache_key)
        if cache_data:
            log.info(f"Get cache - key : {cache_key}")
            return json.loads(cache_data)
        log.info(f"Get bio data from db - user {user_id}")
        query = select(BioDataDB).where(
            and_(BioDataDB.user_id == user_id,
                 BioDataDB.timestamp >= datetime.now() - timedelta(minutes=30))
        ).order_by(
            desc(BioDataDB.timestamp)
        )
        result = await self.db_session.execute(query)
        records = result.scalars().all()
        if records:
            data = [[record.value_1, record.value_2] for record in records]
            await self.redis.set(cache_key, json.dumps(data), ex=self.cache_ttl)
            log.info(f"Set cache - key : {cache_key}")
            return data
        return None
