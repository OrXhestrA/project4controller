import httpx
import asyncio


async def test_upload():
    url = "http://localhost:8000/api/upload_heart_data"
    payload = {
        "user_id": "0001",
        "heart_rate": [
            {
              "rate_id": 1,
              "timestamp": "2025-11-25 08:30:00",
              "value": 72
            },
            {
              "rate_id": 2,
              "timestamp": "2025-11-25 08:31:00",
              "value": 74
            },
            {
              "rate_id": 3,
              "timestamp": "2025-11-25 08:32:00",
              "value": 78
            },
            {
              "rate_id": 4,
              "timestamp": "2025-11-25 08:33:00",
              "value": 81
            },
            {
              "rate_id": 5,
              "timestamp": "2025-11-25 08:34:00",
              "value": 79
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(response.status_code)
        print(response.json())

asyncio.run(test_upload())