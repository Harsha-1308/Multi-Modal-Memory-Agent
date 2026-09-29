import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import chats, evidence, health, messages, projects
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("project_memory_agent")

app = FastAPI(
    title=settings.APP_NAME,
    description="A project-scoped AI workspace with Hindsight memory and evidence tracking",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standardized Error Handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        payload = exc.detail
    else:
        payload = {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        }
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": payload},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception during {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )


# Include API Routers under /api/v1
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(chats.router, prefix="/api/v1", tags=["Chats"])
app.include_router(messages.router, prefix="/api/v1", tags=["Messages"])
app.include_router(evidence.router, prefix="/api/v1", tags=["Evidence"])
