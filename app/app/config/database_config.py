import boto3
from botocore.exceptions import ClientError
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


async def get_s3_client():
    """
    Get s3 Client
    :return:
    """
    log.info("Initializing S3 client")
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.S3_ENDPOINT_URL if settings.S3_ENDPOINT else None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        use_ssl=settings.USE_SSL,
    )
    await _ensure_bucket_exists(s3_client)
    return s3_client


async def _ensure_bucket_exists(s3_client: boto3.client):
    """
    Ensure s3 bucket exist, if not exist, try to create bucket
    :return: None
    """
    try:
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        log.info(f"Bucket {settings.S3_BUCKET_NAME} exists")
    except ClientError as e:
        try:
            s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            log.info(f"Bucket {settings.S3_BUCKET_NAME} created")
        except ClientError as e:
            log.error(f"Error creating S3 bucket : {e}")
