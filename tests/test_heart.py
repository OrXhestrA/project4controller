import pytest
import json
from datetime import datetime
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch
)
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.models.request import HeartDataRequest
from app.models.domain import HeartRateDataDB
from app.repository.cache_aside_storage import CacheAsideRepository


@pytest.fixture
def mock_db_session():
    """mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """mock redis client"""
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def repo(mock_db_session, mock_redis_client):
    """mock cache aside reposi"""
    return CacheAsideRepository(mock_db_session, mock_redis_client)


@pytest.fixture
def sample_heart_data():
    """sample heart data"""
    return HeartDataRequest(
        user_id="test_user",
        heart_rate=[
            {"timestamp": datetime(2025, 11, 26, 10, 1, 0), "value": 80.0},
            {"timestamp": datetime(2025, 11, 26, 10, 2, 0), "value": 90.1},
            {"timestamp": datetime(2025, 11, 26, 10, 3, 0), "value": 100.0}
        ]
    )


class TestInsert:
    """test insert heart data"""

    @pytest.mark.asyncio
    async def test_insert(
            self,
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert heart rate data and delete cache
        :param repo:
        :param mock_db_session:
        :param mock_redis_client:
        :param sample_heart_data:
        :return:
        """
        await repo.insert_heart_data(sample_heart_data)

        assert mock_db_session.add.call_count == 3
        assert mock_db_session.commit.called

        expected_cache_key = f"heart_rate:{sample_heart_data.user_id}:latest"
        mock_redis_client.delete.assert_called_once_with(expected_cache_key)

    @pytest.mark.asyncio
    async def test_insert_with_error(
            self,
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert heart rate data with error
        :param repo:
        :param mock_db_session:
        :param mock_redis_client:
        :param sample_heart_data:
        :return:
        """
        mock_db_session.commit.side_effect = Exception("Database error")
        await repo.insert_heart_data(sample_heart_data)

        assert mock_db_session.add.call_count == 3
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_insert_with_empty(
            self,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        empty = HeartDataRequest(
            user_id="test_user",
            heart_rate=[]
        )
        await repo.insert_heart_data(empty)

        assert mock_db_session.add.call_count == 0
        assert mock_db_session.commit.called
        mock_redis_client.delete.assert_called_once()


class TestGet:
    """test get heart data"""

    @pytest.mark.asyncio
    async def test_get_from_cache_hit(
            self,
            repo,
            mock_redis_client
    ):
        """
        When cache hit
        :param repo:
        :param mock_redis_client:
        :return:
        """
        user_id = "test_user"
        cached_data = [72.0, 80.0, 90.0]
        mock_redis_client.get.return_value = json.dumps(cached_data)

        result = await repo.get_latest_heart_data(user_id)

        assert result == cached_data
        mock_redis_client.get.assert_called_once_with(
            f"heart_rate:{user_id}:latest"
        )
        assert not repo.db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_from_cache_miss(
            self,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        """
        When cache miss
        :param repo:
        :param mock_db_session:
        :param mock_redis_client:
        :return:
        """
        user_id = "test_user"
        mock_redis_client.get.return_value = None

        mock_records = [
            MagicMock(values=lambda: 72.0),
            MagicMock(values=lambda: 80.0),
            MagicMock(values=lambda: 90.0)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_heart_data(user_id, limit=300, ttl=3600)

        assert len(result) == 3
        assert result == [72.0, 80.0, 90.0]

        mock_db_session.execute.assert_called_once()

        cache_key = f"heart_rate:{user_id}:latest"
        mock_redis_client.set.assert_called_once_with(
            cache_key,
            json.dumps(result),
            ex=3600
        )

    @pytest.mark.asyncio
    async def test_get_from_db_no_data(
            self,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        """
        When no data in db
        :param repo:
        :param mock_db_session:
        :param mock_redis_client:
        :return:
        """
        user_id = "test_user"
        mock_redis_client.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_heart_data(user_id)

        assert result == []
        assert not mock_redis_client.set.called

    @pytest.mark.asyncio
    async def test_get_with_invalid_user_id(
            self,
            repo: CacheAsideRepository
    ):
        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data("")

        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data(None)

        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data(123)


class TestCacheAsideIntegration:
    """集成测试：测试插入和获取的完整流程"""

    @pytest.mark.asyncio
    async def test_insert_then_get_workflow(
            self,
            repository,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """测试插入数据后获取数据的完整流程"""
        user_id = sample_heart_data.user_id

        # 1. 插入数据
        await repository.insert_heart_data(sample_heart_data)

        # 验证缓存被删除
        cache_key = f"heart_rate:{user_id}:latest"
        mock_redis_client.delete.assert_called_with(cache_key)

        # 2. 模拟缓存已被删除，获取数据时从数据库读取
        mock_redis_client.get.return_value = None
        mock_records = [MagicMock(values=lambda: 72.0)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_db_session.execute.return_value = mock_result

        result = await repository.get_latest_heart_data(user_id)

        # 验证数据被重新缓存
        assert mock_redis_client.set.called
        assert result == [72.0]


# 运行测试的配置
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])