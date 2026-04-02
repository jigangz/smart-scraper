import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.api.routes import router
from app.scraper.scheduler import JobScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = JobScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    logger.info("Starting scheduler...")
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Stopping scheduler...")
    scheduler.stop()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Smart Scraper API",
    description="A powerful web scraping platform with anti-detection and scheduling",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "Smart Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "jobs": "/api/jobs",
            "stats": "/api/stats",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }
