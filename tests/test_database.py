# tests/test_database.py
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.config.database_config import get_db, get_redis_pool, init_db
import app.config.database_config as db_module


class TestGetDB:
    """测试数据库会话管理"""

    @pytest.mark.asyncio
    async def test_get_db_success(self):
        """测试成功获取数据库会话并提交"""
        # 模拟 AsyncSession
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        with patch('app.database.async_session_maker') as mock_maker, \
                patch('app.database.log') as mock_log:

            # 配置 async context manager
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            # 使用 async generator
            gen = get_db()
            session = await gen.__anext__()

            # 验证返回的是 mock_session
            assert session == mock_session

            # 验证日志
            mock_log.info.assert_any_call("Opening database session")
            mock_log.info.assert_any_call("Begin DB transaction")

            # 此时还未提交
            mock_session.commit.assert_not_called()

            # 模拟正常退出 generator
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

            # 验证提交和关闭
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_log.info.assert_any_call("Closing DB session")

    @pytest.mark.asyncio
    async def test_get_db_with_exception_rollback(self):
        """测试数据库会话异常时执行回滚"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        with patch('app.database.async_session_maker') as mock_maker, \
                patch('app.database.log') as mock_log:
            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            gen = get_db()
            session = await gen.__anext__()

            # 模拟业务逻辑抛出异常
            test_exception = ValueError("Database operation failed")
            with pytest.raises(ValueError, match="Database operation failed"):
                await gen.athrow(test_exception)

            # 验证回滚和关闭
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.commit.assert_not_called()

            # 验证异常日志
            mock_log.exception.assert_called_once_with("rollback DB transaction")
            mock_log.info.assert_any_call("Closing DB session")

    @pytest.mark.asyncio
    async def test_get_db_commit_exception(self):
        """测试提交时发生异常"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=Exception("Commit failed"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        with patch('app.database.async_session_maker') as mock_maker, \
                patch('app.database.log') as mock_log:

            mock_maker.return_value.__aenter__.return_value = mock_session
            mock_maker.return_value.__aexit__.return_value = None

            gen = get_db()
            await gen.__anext__()

            # 模拟正常退出，但 commit 失败
            with pytest.raises(Exception, match="Commit failed"):
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass

            # 验证回滚被调用
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_multiple_calls(self):
        """测试多次调用 get_db 创建独立会话"""
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        with patch('app.database.async_session_maker') as mock_maker:
            mock_maker.return_value.__aenter__.side_effect = [mock_session1, mock_session2]
            mock_maker.return_value.__aexit__.return_value = None

            # 第一次调用
            gen1 = get_db()
            session1 = await gen1.__anext__()

            # 第二次调用
            gen2 = get_db()
            session2 = await gen2.__anext__()

            # 验证是不同的会话
            assert session1 == mock_session1
            assert session2 == mock_session2
            assert session1 != session2


class TestGetRedisPool:
    """测试 Redis 连接池管理"""

    @pytest.mark.asyncio
    async def test_get_redis_pool_first_initialization(self):
        """测试首次初始化 Redis 连接池"""
        # 重置全局变量
        db_module._redis = None

        mock_redis_client = AsyncMock()

        with patch('app.database.redis.from_url', return_value=mock_redis_client) as mock_from_url, \
                patch('app.database.settings') as mock_settings, \
                patch('app.database.log') as mock_log:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_PASSWORD = "letmein123"

            result = await get_redis_pool()

            # 验证 Redis 客户端创建参数
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                password="letmein123",
                encoding="utf-8",
                decode_responses=True
            )

            # 验证日志
            mock_log.info.assert_called_once_with("Initializing Redis connection pool")

            # 验证返回值
            assert result == mock_redis_client
            assert db_module._redis == mock_redis_client

    @pytest.mark.asyncio
    async def test_get_redis_pool_reuse_existing(self):
        """测试复用已存在的 Redis 连接池"""
        mock_redis_client = AsyncMock()

        db_module._redis = mock_redis_client

        with patch('app.database.redis.from_url') as mock_from_url, \
                patch('app.database.log') as mock_log:
            result = await get_redis_pool()

            # 验证不会重新创建
            mock_from_url.assert_not_called()
            mock_log.info.assert_not_called()

            # 验证返回缓存的实例
            assert result == mock_redis_client

    @pytest.mark.asyncio
    async def test_get_redis_pool_without_password(self):
        """测试无密码的 Redis 连接"""
        db_module._redis = None

        mock_redis_client = AsyncMock()

        with patch('app.database.redis.from_url', return_value=mock_redis_client) as mock_from_url, \
                patch('app.database.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_PASSWORD = None  # 无密码

            result = await get_redis_pool()

            mock_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                password=None,
                encoding="utf-8",
                decode_responses=True
            )
            assert result == mock_redis_client

    @pytest.mark.asyncio
    async def test_get_redis_pool_with_empty_password(self):
        """测试空字符串密码"""

        db_module._redis = None

        mock_redis_client = AsyncMock()

        with patch('app.database.redis.from_url', return_value=mock_redis_client) as mock_from_url, \
                patch('app.database.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_PASSWORD = ""  # 空字符串

            result = await get_redis_pool()

            # 空字符串会被当作 None 处理
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                password=None,
                encoding="utf-8",
                decode_responses=True
            )

    @pytest.mark.asyncio
    async def test_get_redis_pool_multiple_calls(self):
        """测试多次调用返回同一实例（单例模式）"""

        db_module._redis = None

        mock_redis_client = AsyncMock()

        with patch('app.database.redis.from_url', return_value=mock_redis_client) as mock_from_url, \
                patch('app.database.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_PASSWORD = "letmein123"

            # 第一次调用
            result1 = await get_redis_pool()
            # 第二次调用
            result2 = await get_redis_pool()
            # 第三次调用
            result3 = await get_redis_pool()

            # 验证只创建一次
            mock_from_url.assert_called_once()

            # 验证返回同一实例
            assert result1 == result2 == result3 == mock_redis_client

    @pytest.mark.asyncio
    async def test_get_redis_pool_connection_error(self):
        """测试 Redis 连接失败"""

        db_module._redis = None

        with patch('app.database.redis.from_url',
                   side_effect=redis.ConnectionError("Connection refused")) as mock_from_url, \
                patch('app.database.settings') as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_PASSWORD = "letmein123"

            with pytest.raises(redis.ConnectionError, match="Connection refused"):
                await get_redis_pool()


class TestInitDB:
    """测试数据库初始化"""

    @pytest.mark.asyncio
    async def test_init_db_success(self):
        """测试成功初始化数据库表"""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        with patch('app.database.engine.begin') as mock_begin, \
                patch('app.database.Base.metadata') as mock_metadata, \
                patch('app.database.log') as mock_log:
            mock_begin.return_value.__aenter__.return_value = mock_conn
            mock_begin.return_value.__aexit__.return_value = None

            await init_db()

            # 验证日志
            mock_log.info.assert_called_once_with("Initializing database")

            # 验证 run_sync 被调用
            mock_conn.run_sync.assert_called_once()

            # 验证传入的是 create_all 方法
            call_args = mock_conn.run_sync.call_args[0][0]
            assert callable(call_args)

    @pytest.mark.asyncio
    async def test_init_db_with_connection_error(self):
        """测试数据库连接失败"""
        with patch('app.database.engine.begin') as mock_begin, \
                patch('app.database.log') as mock_log:
            mock_begin.side_effect = Exception("Connection to MySQL failed")

            with pytest.raises(Exception, match="Connection to MySQL failed"):
                await init_db()

            mock_log.info.assert_called_once_with("Initializing database")

    @pytest.mark.asyncio
    async def test_init_db_with_table_creation_error(self):
        """测试表创建失败"""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock(side_effect=Exception("Table creation failed"))

        with patch('app.database.engine.begin') as mock_begin, \
                patch('app.database.log') as mock_log:
            mock_begin.return_value.__aenter__.return_value = mock_conn
            mock_begin.return_value.__aexit__.return_value = None

            with pytest.raises(Exception, match="Table creation failed"):
                await init_db()

            mock_log.info.assert_called_once_with("Initializing database")
            mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_db_idempotent(self):
        """测试多次初始化的幂等性"""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        with patch('app.database.engine.begin') as mock_begin, \
                patch('app.database.Base.metadata'):
            mock_begin.return_value.__aenter__.return_value = mock_conn
            mock_begin.return_value.__aexit__.return_value = None

            # 多次调用
            await init_db()
            await init_db()
            await init_db()

            # 验证每次都会执行
            assert mock_conn.run_sync.call_count == 3


# 集成测试（需要真实的 MySQL 和 Redis）
class TestDatabaseIntegration:
    """集成测试 - 需要真实的数据库和 Redis 服务"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_mysql_connection(self, db_session):
        """测试真实 MySQL 连接 - 使用 fixture"""
        from sqlalchemy import text

        # 测试简单查询
        result = await db_session.execute(text("SELECT 1 as num"))
        row = result.first()
        assert row[0] == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_mysql_database_name(self, db_session):
        """测试连接到正确的数据库 - 使用 fixture"""
        from sqlalchemy import text

        result = await db_session.execute(text("SELECT DATABASE() as db_name"))
        row = result.first()
        assert row[0] == "heartDb"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_redis_connection(self, redis_client):
        """测试真实 Redis 连接 - 使用 fixture"""

        # 测试基本操作
        test_key = "test:heartDb:key"
        test_value = "test_value_123"

        await redis_client.set(test_key, test_value)
        value = await redis_client.get(test_key)
        assert value == test_value

        # 清理
        await redis_client.delete(test_key)

        # 验证删除
        value = await redis_client.get(test_key)
        assert value is None

    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_mysql_transaction(self, db_session):
    #     """测试 MySQL 事务"""
    #     from sqlalchemy import text
    #
    #     # 开始事务
    #     async with db_session.begin():
    #         await db_session.execute(
    #             text("CREATE TEMPORARY TABLE IF NOT EXISTS test_table (id INT, name VARCHAR(50))")
    #         )
    #         await db_session.execute(
    #             text("INSERT INTO test_table (id, name) VALUES (:id, :name)"),
    #             {"id": 1, "name": "test"}
    #         )
    #
    #     # 验证插入
    #     result = await db_session.execute(text("SELECT * FROM test_table WHERE id = 1"))
    #     row = result.first()
    #     assert row is not None
    #     assert row[1] == "test"
    #
    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_redis_expiration(self, redis_client):
    #     """测试 Redis 过期时间"""
    #     test_key = "test:heartDb:expire"
    #     test_value = "expire_test"
    #
    #     # 设置 1 秒过期
    #     await redis_client.set(test_key, test_value, ex=1)
    #
    #     # 立即获取应该存在
    #     value = await redis_client.get(test_key)
    #     assert value == test_value
    #
    #     # 等待过期
    #     await asyncio.sleep(1.1)
    #
    #     # 应该已经过期
    #     value = await redis_client.get(test_key)
    #     assert value is None

    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_real_redis_with_ttl(self):
    #     """测试 Redis TTL 功能"""
    #
    #     db_module._redis = None
    #
    #     redis_client = await get_redis_pool()
    #
    #     test_key = "test:heartDb:ttl"
    #     test_value = "ttl_test"
    #
    #     # 设置带 TTL 的键
    #     await redis_client.setex(test_key, 5, test_value)  # 5秒过期
    #
    #     # 验证存在
    #     value = await redis_client.get(test_key)
    #     assert value == test_value
    #
    #     # 检查 TTL
    #     ttl = await redis_client.ttl(test_key)
    #     assert 0 < ttl <= 5
    #
    #     # 清理
    #     await redis_client.delete(test_key)
    #
    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_real_init_db(self):
    #     """测试真实数据库初始化"""
    #     # 这会创建所有表
    #     await init_db()
    #
    #     # 验证可以连接
    #     gen = get_db()
    #     session = await gen.__anext__()
    #
    #     # 验证数据库连接正常
    #     result = await session.execute("SELECT DATABASE()")
    #     db_name = result.scalar()
    #     assert db_name == "heartDb"
    #
    #     try:
    #         await gen.__anext__()
    #     except StopAsyncIteration:
    #         pass
    #
    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_transaction_rollback_real(self):
    #     """测试真实事务回滚"""
    #     from app.models.domain import Base
    #
    #     gen = get_db()
    #     session = await gen.__anext__()
    #
    #     try:
    #         # 模拟一些数据库操作
    #         # 然后抛出异常
    #         raise ValueError("Simulated error")
    #     except ValueError:
    #         # 触发回滚
    #         try:
    #             await gen.athrow(ValueError("Simulated error"))
    #         except ValueError:
    #             pass
    #
    #     # 验证会话已关闭
    #     assert session.is_active is False
