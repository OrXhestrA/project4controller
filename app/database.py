from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
import redis.asyncio as redis
from typing import AsyncGenerator
from app.utils import log
from app.config import settings
from app.db_models import Base

DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
REDIS_TTL = settings.REDIS_TTL
REDIS_PASSWORD = settings.REDIS_PASSWORD

DATABASE_ECHO = settings.DATABASE_ECHO

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
redis_pool = None


async def get_redis_pool():
    """
    Get Redis Pool
    :return: redis_pool
    """
    log.info("Initializing Redis connection pool")
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(
            REDIS_URL,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_pool


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
