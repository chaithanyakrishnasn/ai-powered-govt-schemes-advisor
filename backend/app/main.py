import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import (
    LLMUnavailableError,
    ProfileNotFoundError,
    SchemeNotFoundError,
)
from app.core.logging import setup_logging
from app.services.embedding.embedder import GeminiEmbedder
from app.services.llm.gemini import GeminiClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Yojana AI backend...")
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. LLM-related features will be unavailable.")
        gemini_client = None
        embedder = None
    else:
        gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
        embedder = GeminiEmbedder(gemini_client=gemini_client)

    app.state.gemini_client = gemini_client
    app.state.embedder = embedder
    logger.info("Startup complete.")
    yield
    # Shutdown
    logger.info("Shutting down...")


setup_logging()

app = FastAPI(
    title="Yojana AI API",
    description="AI-powered Indian government schemes advisor.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    with logger.contextualize(request_id=request_id):
        start_time = time.monotonic()
        response = await call_next(request)
        process_time = (time.monotonic() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)"
        )
        return response

# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", "N/A"),
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception for {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "request_id": getattr(request.state, "request_id", "N/A"),
        },
    )

@app.exception_handler(SchemeNotFoundError)
async def scheme_not_found_handler(request: Request, exc: SchemeNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "resource": "scheme",
            "slug": exc.slug,
            "request_id": getattr(request.state, "request_id", "N/A"),
        },
    )

@app.exception_handler(ProfileNotFoundError)
async def profile_not_found_handler(request: Request, exc: ProfileNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "resource": "profile",
            "profile_id": str(exc.profile_id),
            "request_id": getattr(request.state, "request_id", "N/A"),
        },
    )

@app.exception_handler(LLMUnavailableError)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_unavailable",
            "message": str(exc),
            "request_id": getattr(request.state, "request_id", "N/A"),
        },
    )

# Routers
app.include_router(v1_router, prefix="/api/v1")
