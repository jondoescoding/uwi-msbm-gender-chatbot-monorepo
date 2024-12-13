from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api.routers import chat_route, keyword_search_route
import os
from typing import List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", "8000"))
HOST = "0.0.0.0" if ENVIRONMENT == "production" else "127.0.0.1"

logger.info(f"Starting application in {ENVIRONMENT} mode")
logger.info(f"Host: {HOST}, Port: {PORT}")

# Define allowed origins based on environment
def get_allowed_origins() -> List[str]:
    if ENVIRONMENT == "production":
        origins = [
            "https://*.onrender.com",  # Allow all Render subdomains
            "https://uwi-msbm-gender-chatbot-frontend-1.onrender.com",  # Your frontend domain
            "https://uwi-msbm-gender-chatbot-frontend-ayta.onrender.com"  # Your backend domain,
            "https://uwi-msbm-gender-chatbot-frontend-1.onrender.com/*"
        ]
        logger.info(f"Production CORS origins: {origins}")
        return origins
    else:
        origins = [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://192.168.64.1:8080",
            "http://localhost:5173"  # Vite's default dev server
        ]
        logger.info(f"Development CORS origins: {origins}")
        return origins

app = FastAPI(
    title="Caribbean Gender News Chat API",
    description="API for chatting with Caribbean gender news data",
    version="1.0.0",
    # Disable automatic trailing slash redirection
    redirect_slashes=False
)

# Configure CORS with dynamic origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# Include routers
app.include_router(chat_route.router, prefix="/chatbot/chat", tags=["chat"])
app.include_router(keyword_search_route.router, prefix="/keyword-search", tags=["keyword-search"])

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to ChatBloom Caribbean API",
        "environment": ENVIRONMENT,
        "version": "1.0.0",
        "port": PORT,
        "host": HOST,
        "allowed_origins": get_allowed_origins()
    }

# Add a health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

# Add startup event handler
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Host: {HOST}")
    logger.info(f"Port: {PORT}")

# Add shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

# Add this for direct execution
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server")
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        timeout_keep_alive=300  # 5 minute keep-alive timeout
    )