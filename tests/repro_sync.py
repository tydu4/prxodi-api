import asyncio
import httpx
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_sync")

BASE_URL = "http://127.0.0.1:8000"

async def test_batch_sync():
    logger.info("Testing Batch Sync...")
    
    # Mock efficient data
    payload = [
        {
            "title": "Test Event 1",
            "slug": "test-event-1",
            "description": "Description 1",
            "full_text": "Full text 1",
            "status": "scheduled",
            "organizer": {"name": "Test Org"},
            "default_venue": {"name": "Test Venue", "city": "Test City", "address": "123 St"},
            "tags": [{"name": "Music", "slug": "music"}, {"name": "Test", "slug": "test"}],
            "occurrences": [
                {"start_time": datetime.now().isoformat(), "status": "scheduled"}
            ],
            "tickets": [{"name": "Standard", "price": 1000}],
            "images": [{"url": "http://example.com/img.jpg"}],
            "sources": [{"source_url": "http://test.com/1", "source_name": "test", "fingerprint": "123"}]
        },
         {
            "title": "Test Event 2",
            "slug": "test-event-2",
            "description": "Description 2",
            "status": "draft",
             # Same tags to test deduplication in batch
             "tags": [{"name": "Music", "slug": "music"}, {"name": "Test", "slug": "test"}],
             "occurrences": [],
             "tickets": [],
             "images": [],
             "sources": []
        }
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{BASE_URL}/events/batch", json=payload)
            logger.info(f"Response Status: {resp.status_code}")
            logger.info(f"Response Body: {resp.text}")
            
            if resp.status_code == 201:
                logger.info("✅ Batch Sync Success")
            else:
                logger.error("❌ Batch Sync Failed")
        except Exception as e:
            logger.error(f"Request failed: {e}")

async def test_get_events():
    logger.info("Testing Get Events...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/events/")
        logger.info(f"Get Events Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Got {len(data)} events")
            logger.info("✅ Get Events Success")
        else:
             logger.error("❌ Get Events Failed")

async def test_get_tags():
    logger.info("Testing Get Tags...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/events/tags")
        logger.info(f"Get Tags Status: {resp.status_code}")
        if resp.status_code == 200:
            logger.info("✅ Get Tags Success")
        else:
             logger.error("❌ Get Tags Failed")

async def main():
    # Wait for server to be up manually or check health
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE_URL}/")
        except:
            logger.warning("Server might not be up. Ensure uvicorn is running.")
            return

    await test_batch_sync()
    await test_get_events()
    await test_get_tags()

if __name__ == "__main__":
    asyncio.run(main())
