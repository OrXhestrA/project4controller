from app.services.storage_service import StorageService
import asyncio

storage_service = StorageService()


async def test():
    result = await storage_service.get_video_data("0001")
    print(result)

if __name__ == '__main__':
    asyncio.run(test())

