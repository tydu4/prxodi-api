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

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Global Exception: {str(exc)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error_log": str(exc)},
    )
