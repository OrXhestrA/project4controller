import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import UserDataRequest
from app.models.dto import UserDataDto, TaskDataDto
from app.repository.cache_aside_storage import CacheAsideRepository


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


class TestUserData:
    """用户数据测试"""

    @pytest.mark.asyncio
    async def test_insert_user_data_success(self, repo, mock_db_session, mock_redis):
        """测试成功插入用户数据"""
        # 准备测试数据
        request = UserDataRequest(
            user_id="user_123",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Software Engineer",
                tasks=[],
                other_info="Test user"
            )
        )

        # 执行
        await repo.insert_user_data(request)

        # 验证
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        mock_redis.delete.assert_called_once_with("user_data:user_123:latest")

    @pytest.mark.asyncio
    async def test_insert_user_data_with_tasks(self, repo, mock_db_session, mock_redis):
        """测试插入带任务的用户数据"""
        request = UserDataRequest(
            user_id="user_456",
            data=UserDataDto(
                age=30,
                gender=0,
                occupation="Manager",
                tasks=[
                    TaskDataDto(task="Task 1"),
                    TaskDataDto(task="Task 2")
                ],
                other_info="User with tasks"
            )
        )

        await repo.insert_user_data(request)

        # 验证用户数据和任务数据都被添加
        assert mock_db_session.add.call_count >= 3  # 1 user + 2 tasks
        assert mock_db_session.commit.call_count >= 3

    @pytest.mark.asyncio
    async def test_insert_user_data_invalid_user_id(self, repo):
        """测试无效的用户ID"""
        request = UserDataRequest(
            user_id="",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Engineer",
                tasks=[],
                other_info="Test"
            )
        )

        with pytest.raises(ValueError, match="Invalid user id"):
            await repo.insert_user_data(request)

    @pytest.mark.asyncio
    async def test_insert_user_data_invalid_gender(self, repo):
        """测试无效的性别"""
        request = UserDataRequest(
            user_id="user_789",
            data=UserDataDto(
                age=25,
                gender=2,  # 无效值
                occupation="Engineer",
                tasks=[],
                other_info="Test"
            )
        )

        with pytest.raises(ValueError, match="Invalid gender"):
            await repo.insert_user_data(request)

    @pytest.mark.asyncio
    async def test_insert_user_data_db_error(self, repo, mock_db_session):
        """测试数据库错误处理"""
        mock_db_session.commit.side_effect = Exception("DB Error")

        request = UserDataRequest(
            user_id="user_error",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Engineer",
                tasks=[],
                other_info="Test"
            )
        )

        await repo.insert_user_data(request)

        # 验证回滚被调用
        mock_db_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_data_from_cache(self, repo, mock_redis):
        """测试从缓存获取用户数据"""
        user_id = "user_cache"
        cached_data = {
            "user_id": user_id,
            "age": 25,
            "gender": 1,
            "occupation": "Engineer",
            "other_info": "Cached user"
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await repo.get_user_data(user_id)

        assert result == cached_data
        mock_redis.get.assert_called_once_with(f"user_data:{user_id}:latest")

    @pytest.mark.asyncio
    async def test_get_user_data_from_db(self, repo, mock_db_session, mock_redis):
        """测试从数据库获取用户数据"""
        user_id = "user_db"
        mock_redis.get.return_value = None

        # 模拟数据库返回
        mock_record = MagicMock()
        mock_record.values.return_value = {
            "user_id": user_id,
            "age": 30,
            "gender": 0,
            "occupation": "Manager"
        }

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_record
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_user_data(user_id)

        assert result["user_id"] == user_id
        assert result["age"] == 30
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_data_not_found(self, repo, mock_db_session, mock_redis):
        """测试用户数据不存在"""
        user_id = "user_notfound"
        mock_redis.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_user_data(user_id)

        assert result is None


class TestTaskData:
    """任务数据测试"""

    @pytest.mark.asyncio
    async def test_insert_task_data_success(self, repo, mock_db_session, mock_redis):
        """测试成功插入任务数据"""
        request = UserDataRequest(
            user_id="user_task",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Engineer",
                tasks=[
                    TaskDataDto(task="Complete project"),
                    TaskDataDto(task="Review code")
                ],
                other_info="Test"
            )
        )

        await repo.insert_task_data(request)

        assert mock_db_session.add.call_count == 2
        assert mock_db_session.commit.call_count == 2
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_insert_task_data_empty_list(self, repo, mock_db_session):
        """测试空任务列表"""
        request = UserDataRequest(
            user_id="user_notask",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Engineer",
                tasks=[],
                other_info="Test"
            )
        )

        await repo.insert_task_data(request)

        assert mock_db_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_insert_task_data_error(self, repo, mock_db_session):
        """测试任务数据插入错误"""
        mock_db_session.commit.side_effect = Exception("Task DB Error")

        request = UserDataRequest(
            user_id="user_task_error",
            data=UserDataDto(
                age=25,
                gender=1,
                occupation="Engineer",
                tasks=[TaskDataDto(task="Test task")],
                other_info="Test"
            )
        )

        await repo.insert_task_data(request)

        mock_db_session.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_get_task_data_from_cache(self, repo, mock_redis):
        """测试从缓存获取任务数据"""
        user_id = "user_task_cache"
        cached_tasks = [
            {"task": "Task 1", "timestamp": "2025-11-26T18:00:00"},
            {"task": "Task 2", "timestamp": "2025-11-26T18:10:00"}
        ]
        mock_redis.get.return_value = json.dumps(cached_tasks)

        result = await repo.get_task_data(user_id)

        assert result == cached_tasks
        mock_redis.get.assert_called_once_with(f"task_data:{user_id}:latest")

    @pytest.mark.asyncio
    async def test_get_task_data_from_db(self, repo, mock_db_session, mock_redis):
        """测试从数据库获取任务数据"""
        user_id = "user_task_db"
        mock_redis.get.return_value = None

        # 模拟数据库返回多条记录
        mock_record1 = MagicMock()
        mock_record1.values.return_value = {"task": "Task 1", "user_id": user_id}
        mock_record2 = MagicMock()
        mock_record2.values.return_value = {"task": "Task 2", "user_id": user_id}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record1, mock_record2]
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_task_data(user_id)

        assert len(result) == 2
        assert result[0]["task"] == "Task 1"
        assert result[1]["task"] == "Task 2"
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_data_not_found(self, repo, mock_db_session, mock_redis):
        """测试任务数据不存在"""
        user_id = "user_task_notfound"
        mock_redis.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_task_data(user_id)

        assert result is None


# 集成测试
class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, repo, mock_db_session, mock_redis):
        """测试完整工作流:插入后获取"""
        # 插入数据
        request = UserDataRequest(
            user_id="user_integration",
            data=UserDataDto(
                age=28,
                gender=1,
                occupation="DevOps Engineer",
                tasks=[TaskDataDto(task="Deploy service")],
                other_info="Integration test"
            )
        )

        await repo.insert_user_data(request)

        # 模拟获取数据
        mock_redis.get.return_value = None
        mock_record = MagicMock()
        mock_record.values.return_value = {
            "user_id": "user_integration",
            "age": 28,
            "gender": 1,
            "occupation": "DevOps Engineer"
        }

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_record
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_user_data("user_integration")

        assert result["user_id"] == "user_integration"
        assert result["age"] == 28
