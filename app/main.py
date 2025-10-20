import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import get_settings
from app.routers import report_router

# 설정 로드
settings = get_settings()

# 구조화된 로깅 설정
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.log_level.upper(), structlog.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    logger.info(
        "application_startup",
        version="1.0.0",
        environment="production"
    )
    yield
    # 종료 시
    logger.info("application_shutdown")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="QBIT-AI Report Service",
    description="QBIT 주식 모의투자 플랫폼의 AI 분석 서버",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate Limiter 상태 설정
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 민감정보 필터링 (Authorization 헤더는 로깅하지 않음)
    safe_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["authorization"]
    }

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
        headers=safe_headers
    )

    response = await call_next(request)

    logger.info(
        "http_response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code
    )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "내부 서버 오류가 발생했습니다.",
            "error_type": type(exc).__name__
        }
    )


# 라우터 등록
app.include_router(report_router)


@app.get(
    "/",
    summary="Root Endpoint",
    description="API 서버 기본 정보",
)
@limiter.limit("10/minute")
async def root(request: Request) -> dict[str, str]:
    return {
        "service": "QBIT-AI Report Service",
        "version": "1.0.0",
        "description": "주식 모의투자 AI 분석 서버",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
        log_level=settings.log_level.lower()
    )

