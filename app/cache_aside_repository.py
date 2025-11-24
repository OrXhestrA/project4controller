from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db_models import (
    HeartRateDataDB,
    VideoDataDB,
    UserDataDB,
    TaskDataDB,
    BioDataDB
)
from datetime import datetime
import json
from app.utils import log
from typing import List, Any
from redis import Redis


class CacheAsideRepository:
    def __init__(self, db: AsyncSession, redis_client: Redis):
        self.db_session = db
        self.redis = redis_client
        log.info("init cache aside repository")

    async def _get_cache(self, key: str):
        """

        :param key:
        :return:
        """
        log.info(f"get cache - key : {key}")
        cached = await self.redis.get(key)
        if cached:
            log.info(f"cache hit - key : {key}")
            return json.loads(cached)
        log.info(f"cache miss - key : {key}")
        return None

    async def _set_cache(self, key: str, value, ttl: int):
        """

        :param key:
        :param value:
        :param ttl:
        :return:
        """
        log.info(f"set cache - key : {key}")
        await self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        val = await self.redis.get(key)
        log.info(f"get cache - key : {key}, value : {val}")

    async def _invalidate_cache(self, *keys):
        """

        :param keys:
        :return:
        """
        log.info(f"invalidate cache - keys : {keys}")
        if keys:
            removed = await self.redis.delete(*keys)
            log.debug(f"Invalidated cache keys {keys}: {removed} removed")

    async def insert_heart_rate_data(self, user_id: str, heart_data: list, ttl=3600):
        """

        :param user_id:
        :param heart_data:
        :param ttl:
        :return:
        """
        for data in heart_data:
            log.info(f"insert heart rate data - user : {user_id}, data : {data}")
            record = HeartRateDataDB(
                user_id=user_id,
                timestamp=datetime.fromisoformat(data['timestamp']),
                value=data['value']
            )
            log.debug(f"insert heart rate data - user : {user_id}, data : {data}")
            self.db_session.add(record)

        await self.db_session.flush()

        key = f"heart_rate:{user_id}:latest"
        await self._set_cache(key, heart_data, ttl)
        log.info(f"insert heart rate data - user : {user_id}")

    async def get_latest_heart_rate_data(self, user_id: str, limit=300, ttl=7200) -> List[Any]:
        """

        :param user_id:
        :param limit:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        key = f"heart_rate:{user_id}:latest"
        cache_data = await self._get_cache(key)
        if cache_data:
            log.debug(f"get latest heart rate data from cache - user : {user_id}")
            data = [r.values for r in cache_data]
            return data

        stmt = (
            select(HeartRateDataDB)
            .where(HeartRateDataDB.user_id == user_id)
            .order_by(desc(HeartRateDataDB.timestamp))
            .limit(limit)
        )
        result = await self.db_session.execute(stmt)
        records = result.scalars().all()

        data = [r.values() for r in records]

        if data:
            log.debug(f"get latest heart rate data from db - user : {user_id}")
            await self._set_cache(key, data, ttl)
        return data

    async def insert_video_data(self, user_id: str, video_data: list, ttl=3600):
        """

        :param user_id:
        :param video_data:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        records = []
        for data in video_data:
            record = VideoDataDB(
                user_id=user_id,
                timestamp=datetime.fromisoformat(data['timestamp']),
                format=data['format'],
                data=data['data']
            )
            self.db_session.add(record)
            records.append(record)

        await self.db_session.flush()
        keys = [f"video:{user_id}:latest"]
        await self._invalidate_cache(*keys)
        log.info(f"insert video data - user : {user_id}")
        return records

    async def get_latest_video_data(self, user_id: str, limit=10, ttl=3600):
        """

        :param user_id:
        :param limit:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        key = f"video:{user_id}:latest"
        cache_data = await self._get_cache(key)
        if cache_data:
            log.debug(f"get latest video data from cache - user : {user_id}")
            return cache_data

        stmt = (
            select(VideoDataDB)
            .where(VideoDataDB.user_id == user_id)
            .order_by(desc(VideoDataDB.timestamp))
            .limit(limit)
        )
        result = await self.db_session.execute(stmt)
        records = result.scalars().all()
        data = [
            {
                "video_id": r.video_id,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "format": r.format,
                "data": r.data
            } for r in records
        ]
        if data:
            log.debug(f"get latest video data from db - user : {user_id}")
            await self._set_cache(key, data, ttl)
        return data

    async def insert_user_data(self, user_id: str, user_data, ttl=3600):
        """

        :param user_id:
        :param user_data:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        record = UserDataDB(
            user_id=user_id,
            age=user_data['age'],
            gender=user_data['gender'],
            occupation=user_data['occupation'],
            other_info=user_data['other_info']
        )
        self.db_session.add(record)
        await self.db_session.flush()
        keys = [f"user:{user_id}:latest"]
        await self._invalidate_cache(*keys)
        log.info(f"insert user data - user : {user_id}")
        return record

    async def get_latest_user_data(self, user_id: str, ttl=3600):
        """

        :param user_id:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        key = f"user:{user_id}:latest"
        cache_data = await self._get_cache(key)
        if cache_data:
            log.debug(f"get latest user data from cache - user : {user_id}")
            return cache_data

        stmt = (
            select(UserDataDB)
            .where(UserDataDB.user_id == user_id)
            .order_by(desc(UserDataDB.timestamp))
            .limit(1)
        )
        result = await self.db_session.execute(stmt)
        record = result.scalars().first()
        data = {
            "user_id": record.user_id,
            "age": record.age,
            "gender": record.gender,
            "occupation": record.occupation,
            "other_info": record.other_info
        }
        if data:
            log.debug(f"get latest user data from db - user : {user_id}")
            await self._set_cache(key, data, ttl)
        return data

    async def insert_task_data(self, user_id: str, user_data: dict, ttl=3600):
        """

        :param user_id:
        :param user_data:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        records = []
        for data in user_data["tasks"]:
            record = TaskDataDB(
                user_id=user_id,
                task=data['task'],
                timestamp=datetime.fromisoformat(data['timestamp'])
            )
            self.db_session.add(record)
            records.append(record)
        await self.db_session.flush()
        keys = [f"task:{user_id}:latest"]
        await self._invalidate_cache(*keys)
        log.info(f"insert task data - user : {user_id}")
        return records

    async def get_latest_task_data(self, user_id: str, limit=10, ttl=3600):
        """

        :param user_id:
        :param limit:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        key = f"task:{user_id}:latest"
        cache_data = await self._get_cache(key)
        if cache_data:
            log.debug(f"get latest task data from cache - user : {user_id}")
            return cache_data
        stmt = (
            select(TaskDataDB)
            .where(TaskDataDB.user_id == user_id)
            .order_by(desc(TaskDataDB.timestamp))
            .limit(limit)
        )
        result = await self.db_session.execute(stmt)
        records = result.scalars().all()
        data = [
            {
                "task_id": r.task_id,
                "task": r.task,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            } for r in records
        ]
        if data:
            log.debug(f"get latest task data from db - user : {user_id}")
            await self._set_cache(key, data, ttl)
        return data

    async def insert_bio_data(self, user_id: str, bio_data: list, ttl=3600):
        """

        :param user_id:
        :param bio_data:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        records = []
        for data in bio_data:
            record = BioDataDB(
                user_id=user_id,
                timestamp=datetime.fromisoformat(data['timestamp']),
                value_1=data['value_1'],
                value_2=data['value_2']
            )
            self.db_session.add(record)
            records.append(record)
        await self.db_session.flush()
        keys = [f"bio:{user_id}:latest"]
        await self._invalidate_cache(*keys)
        log.info(f"insert bio data - user : {user_id}")
        return records

    async def get_latest_bio_data(self, user_id: str, limit=10, ttl=3600):
        """

        :param user_id:
        :param limit:
        :param ttl:
        :return:
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid user_id")
        key = f"bio:{user_id}:latest"
        cache_data = await self._get_cache(key)
        if cache_data:
            log.debug(f"get latest bio data from cache - user : {user_id}")
            return cache_data

        stmt = (
            select(BioDataDB)
            .where(BioDataDB.user_id == user_id)
            .order_by(desc(BioDataDB.timestamp))
            .limit(limit)
        )
        result = await self.db_session.execute(stmt)
        records = result.scalars().all()
        data = [
            {
                "bio_id": r.bio_id,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "value_1": r.value_1,
                "value_2": r.value_2
            } for r in records
        ]
        if data:
            log.debug(f"get latest bio data from db - user : {user_id}")
            await self._set_cache(key, data, ttl)
        return data

