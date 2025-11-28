import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.repository.cache_aside_storage import CacheAsideRepository
from app.models.request import HeartDataRequest


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """模拟 Redis 客户端"""
    redis = AsyncMock(spec=Redis)
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def repo(mock_db_session, mock_redis_client):
    """创建 CacheAsideRepository 实例"""
    return CacheAsideRepository(mock_db_session, mock_redis_client)


@pytest.fixture
def sample_heart_data():
    """示例心率数据"""
    return HeartDataRequest(
        user_id="test_user",
        heart_rate=[
            {"timestamp": "2025-11-26 10:01:00", "value": 80.0},
            {"timestamp": "2025-11-26 10:02:00", "value": 85.0},
            {"timestamp": "2025-11-26 10:03:00", "value": 90.0}
        ]
    )


class TestInsert:
    """测试 insert_heart_data 方法"""

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')
    async def test_insert(
            self,
            mock_heart_rate_db,
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert heart rate data and delete cache
        """
        mock_heart_rate_db.return_value = MagicMock()

        # 执行
        await repo.insert_heart_data(sample_heart_data)

        # 验证 HeartRateDataDB 被调用了 3 次
        assert mock_heart_rate_db.call_count == 3

        # 验证数据库操作
        assert mock_db_session.add.call_count == 3
        assert mock_db_session.commit.called

        # 验证缓存删除
        expected_cache_key = f"heart_rate:{sample_heart_data.user_id}:latest"
        mock_redis_client.delete.assert_called_once_with(expected_cache_key)

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')  # 添加这个装饰器
    async def test_insert_with_error(
            self,
            mock_heart_rate_db,  # 添加这个参数
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert heart rate data with database error
        """
        # Mock HeartRateDataDB
        mock_heart_rate_db.return_value = MagicMock()

        # 模拟数据库提交失败
        mock_db_session.commit.side_effect = Exception("Database error")

        # 执行并验证抛出异常
        with pytest.raises(Exception, match="Database error"):
            await repo.insert_heart_data(sample_heart_data)

        # 验证数据仍然被添加到 session（即使 commit 失败）
        assert mock_db_session.add.call_count == 3
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')
    async def test_insert_with_redis_error(
            self,
            mock_heart_rate_db,
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert heart rate data with Redis delete error
        Redis 错误不应该影响数据库操作
        """
        mock_heart_rate_db.return_value = MagicMock()

        # 模拟 Redis 删除失败
        mock_redis_client.delete.side_effect = Exception("Redis connection error")

        # 执行（不应该抛出异常，因为代码中有 try-except）
        await repo.insert_heart_data(sample_heart_data)

        # 验证数据库操作仍然完成
        assert mock_db_session.add.call_count == 3
        assert mock_db_session.commit.called

        # 验证尝试删除缓存
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')
    async def test_insert_empty_list(
            self,
            mock_heart_rate_db,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        """
        Test insert empty heart rate data list
        """
        mock_heart_rate_db.return_value = MagicMock()

        empty_data = HeartDataRequest(user_id="test_user", heart_rate=[])

        await repo.insert_heart_data(empty_data)

        # 验证没有插入数据
        assert mock_heart_rate_db.call_count == 0
        assert mock_db_session.add.call_count == 0

        # 但仍然提交和删除缓存
        assert mock_db_session.commit.called
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')
    async def test_insert_single_record(
            self,
            mock_heart_rate_db,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        """
        Test insert single heart rate record
        """
        mock_heart_rate_db.return_value = MagicMock()

        single_data = HeartDataRequest(
            user_id="test_user",
            heart_rate=[
                {"timestamp": "2025-11-26 10:01:00", "value": 75.0}
            ]
        )

        await repo.insert_heart_data(single_data)

        # 验证只插入一条数据
        assert mock_heart_rate_db.call_count == 1
        assert mock_db_session.add.call_count == 1
        assert mock_db_session.commit.called
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.repository.cache_aside_storage.HeartRateDataDB')
    async def test_insert_verify_db_data_structure(
            self,
            mock_heart_rate_db,
            repo,
            mock_db_session,
            mock_redis_client,
            sample_heart_data
    ):
        """
        Test insert and verify the structure of data passed to HeartRateDataDB
        """
        mock_heart_rate_db.return_value = MagicMock()

        await repo.insert_heart_data(sample_heart_data)

        # 验证每次调用 HeartRateDataDB 的参数
        calls = mock_heart_rate_db.call_args_list

        # 第一条数据
        assert calls[0][1]['user_id'] == 'test_user'
        assert calls[0][1]['timestamp'] == '2025-11-26 10:01:00'
        assert calls[0][1]['heart_rate'] == 80.0

        # 第二条数据
        assert calls[1][1]['user_id'] == 'test_user'
        assert calls[1][1]['timestamp'] == '2025-11-26 10:02:00'
        assert calls[1][1]['heart_rate'] == 85.0

        # 第三条数据
        assert calls[2][1]['user_id'] == 'test_user'
        assert calls[2][1]['timestamp'] == '2025-11-26 10:03:00'
        assert calls[2][1]['heart_rate'] == 90.0


class TestGetLatestHeartData:
    """测试 get_latest_heart_data 方法"""

    @pytest.mark.asyncio
    async def test_get_from_cache_hit(self, repo, mock_redis_client):
        """测试缓存命中"""
        user_id = "test_user"
        cached_data = [72.0, 75.0, 73.0]
        mock_redis_client.get.return_value = json.dumps(cached_data)

        result = await repo.get_latest_heart_data(user_id)

        assert result == cached_data
        mock_redis_client.get.assert_called_once_with(f"heart_rate:{user_id}:latest")
        assert not repo.db_session.execute.called

    @pytest.mark.asyncio
    async def test_get_from_db_cache_miss(
            self,
            repo,
            mock_db_session,
            mock_redis_client
    ):
        """测试缓存未命中，从数据库获取"""
        user_id = "test_user"
        mock_redis_client.get.return_value = None

        # 模拟数据库返回数据
        mock_records = [
            MagicMock(values=lambda: 72.0),
            MagicMock(values=lambda: 75.0),
            MagicMock(values=lambda: 73.0),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_heart_data(user_id, limit=300, ttl=3600)

        assert len(result) == 3
        assert result == [72.0, 75.0, 73.0]

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
        """测试数据库无数据"""
        user_id = "test_user"
        mock_redis_client.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_heart_data(user_id)

        assert result == []
        assert not mock_redis_client.set.called

    @pytest.mark.asyncio
    async def test_get_with_invalid_user_id(self, repo):
        """测试无效的 user_id"""
        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data("")

        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data(None)

        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.get_latest_heart_data(123)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
