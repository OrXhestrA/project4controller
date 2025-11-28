from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
import redis.asyncio as redis
from typing import AsyncGenerator
from app.utils.logger import log
from app.config.base_config import settings
from app.models.domain import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
_redis = None


async def get_redis_pool():
    """
    Get Redis Pool
    :return: redis_pool
    """
    global _redis
    if _redis is None:
        log.info("Initializing Redis connection pool")
        _redis = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    GET Database Session
    :return: AsyncGenerator
    """
    log.info("Opening database session")
    async with async_session_maker() as session:
        try:
            log.info("Begin DB transaction")
            yield session
            await session.commit()
        except Exception:
            log.exception("rollback DB transaction")
            await session.rollback()
            raise
        finally:
            log.info("Closing DB session")
            await session.close()


async def init_db():
    """
    Auto create table (in startup event)
    :return: None
    """
    log.info("Initializing database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
