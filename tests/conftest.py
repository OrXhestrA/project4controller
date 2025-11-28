# tests/conftest.py
import pytest
import asyncio
from typing import Generator, AsyncGenerator
import sys

# 修复 Windows 上的事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="function")
def event_loop():
    """为每个测试函数创建新的事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # 确保所有任务完成
    try:
        # 取消所有待处理的任务
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        # 运行直到所有任务完成
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def reset_database_globals():
    """每个测试后重置数据库全局变量"""
    yield
    import app.config.database_config as db_module
    db_module._redis = None
    db_module._engine = None  # 也重置 engine


@pytest.fixture
def mock_mysql_settings():
    """模拟 MySQL 配置"""
    from unittest.mock import MagicMock
    settings = MagicMock()
    settings.DATABASE_URL = "mysql+aiomysql://root:root123@localhost:3306/heartDb?charset=utf8mb4"
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.REDIS_PASSWORD = "letmein123"
    settings.REDIS_TTL = 3600
    settings.DATABASE_ECHO = False
    return settings


@pytest.fixture
def mock_redis_settings():
    """模拟 Redis 配置"""
    from unittest.mock import MagicMock
    settings = MagicMock()
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.REDIS_PASSWORD = "letmein123"
    settings.REDIS_TTL = 3600
    return settings


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator:
    """提供数据库会话的 fixture - 直接创建 session 而不是使用 get_db()"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.config.base_config import settings

    # 创建临时 engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # 创建 session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 创建 session
    async with async_session_maker() as session:
        yield session

    # 清理
    await engine.dispose()


@pytest.fixture(scope="function")
async def redis_client():
    """提供 Redis 客户端的 fixture"""
    from redis import asyncio as aioredis
    from app.config.base_config import settings
    import app.config.database_config as db_module

    # 重置全局变量
    db_module._redis = None

    # 直接创建 Redis 客户端
    client = await aioredis.from_url(
        settings.REDIS_URL,
        password=settings.REDIS_PASSWORD,
        encoding="utf-8",
        decode_responses=True,
    )

    yield client

    # 清理测试数据
    try:
        keys = await client.keys("test:heartDb:*")
        if keys:
            await client.delete(*keys)
    finally:
        await client.aclose()
