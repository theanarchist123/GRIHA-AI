from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.connection import init_db
from config import settings
from api.routes import router as api_router
import asyncio
import sys
from services.price_monitor import monitor_prices_loop

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Starting up Griha AI Backend...")
    await init_db()
    
    # Start background price monitor
    price_monitor_task = asyncio.create_task(monitor_prices_loop())
    
    yield
    
    # Shutdown actions
    print("Shutting down Griha AI Backend...")
    price_monitor_task.cancel()

app = FastAPI(
    title="Griha AI API",
    description="Backend API for Griha AI property platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS framework for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Render and generic health check endpoint."""
    return {"status": "ok", "app_env": settings.app_env}

app.include_router(api_router)
