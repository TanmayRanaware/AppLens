"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routes import auth, repos, scan, graph, chat, nlq
from app.db.base import engine, Base
import logging
import sys

# Configure logging to output to stdout with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AppLens API",
    description="Microservice Dependency Visualization API",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(nlq.router, prefix="/nlq", tags=["nlq"])


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    logger.info("Starting AppLens backend...")
    try:
        # Create tables (in production, use Alembic migrations)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}. Tables may already exist.")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "applens-backend",
            "version": "0.1.0",
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AppLens API", "docs": "/docs"}

