import asyncio
from app.database import get_redis_pool


async def test_redis_connection():
    async with await get_redis_pool() as redis_client:
        pong = await redis_client.ping()
        if pong:
            print("Redis connection successful")
        else:
            print("Redis connection failed")


if __name__ == '__main__':
    asyncio.run(test_redis_connection())