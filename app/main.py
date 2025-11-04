import structlog
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException
from app.config import get_settings
from app.routers import report_router, news_router
from app.routers.news import init_services as init_news_services
from app.services.db_service import DatabaseService
from app.services.liquid_stocks_service import LiquidStocksService
from app.services.correlation_service import CorrelationService

# 설정 로드
settings = get_settings()

# 구조화된 로깅 설정
import logging
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)

# 스케줄러 설정
scheduler = AsyncIOScheduler()

# 서비스 인스턴스 (lifespan에서 초기화)
db_service = DatabaseService()
liquid_stocks_service = LiquidStocksService()
correlation_service = CorrelationService()


async def update_liquid_stocks_job():
    """
    주 1회 유동성 Top 3000 종목 리스트 업데이트
    """
    try:
        logger.info("liquid_stocks_update_job_started")
        count = await liquid_stocks_service.update_liquid_stocks()
        logger.info("liquid_stocks_update_job_completed", updated_count=count)
    except Exception as e:
        logger.error(
            "liquid_stocks_update_job_failed",
            error=str(e),
            error_type=type(e).__name__
        )


async def update_correlations_job():
    """
    주 1회 상관계수 계산 및 저장 (유동성 종목 업데이트 후 실행)
    """
    try:
        logger.info("correlations_update_job_started")
        result = await correlation_service.calculate_and_save_correlations(
            days=90,
            max_concurrent=8
        )
        if result.get("success"):
            logger.info(
                "correlations_update_job_completed",
                processed_tickers=result.get("processed_tickers"),
                correlations_saved=result.get("correlations_saved")
            )
        else:
            logger.error(
                "correlations_update_job_failed",
                error=result.get("error")
            )
    except Exception as e:
        logger.error(
            "correlations_update_job_failed",
            error=str(e),
            error_type=type(e).__name__
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    logger.info(
        "application_startup",
        version="1.0.0",
        environment="production"
    )
    
    # DB 연결
    try:
        await db_service.connect()
        logger.info("database_connected")
        
        # Liquid stocks 서비스 초기화
        await liquid_stocks_service.initialize(db_service)
        logger.info("liquid_stocks_service_initialized")
        
        # Correlation 서비스 초기화
        await correlation_service.initialize(liquid_stocks_service, db_service)
        logger.info("correlation_service_initialized")
        
        # News 라우터 서비스 초기화
        init_news_services(db_service, liquid_stocks_service, correlation_service, limiter)
        logger.info("news_router_initialized")
        
        # 스케줄러 등록
        # 주 1회 (일요일 새벽 3시) Top 3000 업데이트
        scheduler.add_job(
            update_liquid_stocks_job,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='update_liquid_stocks',
            name='Update Liquid Stocks Top 3000',
            replace_existing=True
        )
        
        # 주 1회 (일요일 새벽 3시 5분) 상관계수 계산 (유동성 종목 업데이트 후 실행)
        scheduler.add_job(
            update_correlations_job,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=5),
            id='update_correlations',
            name='Update Correlations',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("scheduler_started")
        
    except Exception as e:
        logger.error(
            "application_startup_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    
    yield
    
    # 종료 시
    try:
        scheduler.shutdown()
        await db_service.close()
        logger.info("application_shutdown")
    except Exception as e:
        logger.error(
            "application_shutdown_error",
            error=str(e)
        )


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
app.include_router(news_router)


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

