from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import init_async_db
from routers import events
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Database...")
    await init_async_db()
    yield
    # Shutdown

app = FastAPI(title="Event Parser API", lifespan=lifespan)

app.include_router(events.router)

@app.get("/")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
