# app/main.py

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

# DB 및 설정
from app.core.db import init_db, close_db, async_session_factory
from app.core.config import settings

# 모델 Import (테이블 생성용)
from app.models.user import User
from app.models.auth import SocialAccount, AuthSession
from app.models.user_context import UserContext
from app.models.terms import TermsAgreement
from app.models.enums import GenderType, UserRole, UserTier, PlatformType

# API 라우터
from app.api.v1 import auth, users, memory, debug

# Socket Modules
from app.sockets.manager import socket_manager
import app.sockets.events  # [필수] 이벤트 핸들러 등록

# Security Middleware
from app.middleware.security import HTTPSRedirectMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 필수 환경 변수 검증
    logger.info("🔐 환경 변수 검증 중...")
    settings.validate_required()
    logger.info("✅ 필수 환경 변수 확인 완료")

    # 서버 기동 시 DB 초기화
    logger.info("🚀 사만다를 깨우는 중...")
    await init_db()
    logger.info("✅ 모든 데이터베이스 테이블이 준비되었습니다.")

    # Socket idle monitor 시작
    await socket_manager.start_background_task()
    logger.info("✅ Socket idle monitor 시작됨")

    # Kiwi 형태소 분석기 warm-up (첫 요청 ~1,200ms 페널티 제거)
    try:
        from app.engine.memory import get_kiwi, get_memory_engine
        get_kiwi()
        logger.info("✅ Kiwi 형태소 분석기 로딩 완료")
    except Exception as e:
        logger.warning("⚠️ Kiwi warm-up 실패 (non-critical): %s", e)

    # OpenAI 임베딩 커넥션 풀 warm-up (첫 요청 ~800ms 핸드셰이크 제거)
    try:
        memory_engine = get_memory_engine()
        await memory_engine.get_embedding("warmup")
        logger.info("✅ OpenAI 임베딩 커넥션 풀 warm-up 완료")
    except Exception as e:
        logger.warning("⚠️ OpenAI embedding warm-up 실패 (non-critical): %s", e)

    # Context Cache warm-up (설정 활성화 시)
    if settings.USE_CONTEXT_CACHE:
        try:
            from app.integrations.llm.gemini_provider import get_cache_manager
            cache_manager = get_cache_manager()
            from app.engine.prompts import ACTOR_SYSTEM_PROMPT
            await cache_manager.get_cache("actor", ACTOR_SYSTEM_PROMPT, settings.ACTOR_MODEL)

            logger.info("✅ Gemini Context Cache 준비 완료")
        except Exception as e:
            logger.warning("⚠️ Context Cache 초기화 실패 (fallback 모드): %s", e)

    # Gemini HTTP/2 Connection Pool warm-up (캐시 비활성화 시에도 연결 준비)
    try:
        from app.integrations.llm.gemini_provider import warm_up_connections
        await warm_up_connections()
        logger.info("✅ Gemini Connection Pool warm-up 완료")
    except Exception as e:
        logger.warning("⚠️ Connection warm-up 실패 (non-critical): %s", e)

    yield

    # Socket idle monitor 종료
    await socket_manager.stop_background_task()
    logger.info("✅ Socket idle monitor 종료됨")

    # 서버 종료 시 캐시 정리
    if settings.USE_CONTEXT_CACHE:
        try:
            from app.integrations.llm.gemini_provider import get_cache_manager
            cache_manager = get_cache_manager()
            await cache_manager.cleanup()
            logger.info("✅ Gemini Context Cache 정리 완료")
        except Exception as e:
            logger.warning("⚠️ Context Cache 정리 실패: %s", e)

    # 데이터베이스 연결 정리
    await close_db()
    logger.info("✅ 데이터베이스 연결 정리 완료")
    logger.info("💤 사만다가 잠에 듭니다.")


app = FastAPI(
    title="Samantha Project API",
    description="시니어를 위한 영혼의 동반자, 사만다 백엔드",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 미들웨어 (settings에서 관리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안 헤더 미들웨어 (항상 활성화)
force_https_flag = True if settings.ENVIRONMENT == "production" else getattr(settings, 'FORCE_HTTPS', False)
app.add_middleware(SecurityHeadersMiddleware, force_https=force_https_flag)

# HTTPS 보안 미들웨어 (프로덕션에서만 활성화)
# 미들웨어는 역순으로 실행되므로 HTTPSRedirect가 가장 먼저 실행되도록 가장 마지막에 추가
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware, force_https=True)
else:
    # 개발 환경에서는 HTTPS 강제를 비활성화 (설정으로 제어 가능)
    force_https = settings.FORCE_HTTPS if hasattr(settings, 'FORCE_HTTPS') else False
    app.add_middleware(HTTPSRedirectMiddleware, force_https=force_https)

# 라우터 등록
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
if settings.ENVIRONMENT == "development":
    app.include_router(debug.router, prefix="/api/v1/debug", tags=["Debug"])

# 소켓 서버 마운트
socket_manager.mount_to_app(app, path="/ws/socket.io")


@app.get("/")
async def root():
    """루트 경로 - 기본 API 정보 제공"""
    return {
        "service": "Samantha Project API",
        "version": "0.1.0",
        "status": "alive",
        "message": "사만다가 대기 중입니다",
        "endpoints": {
            "health": "/health",
            "api": "/api/v1",
            "websocket": "/ws/socket.io"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "alive", "message": "사만다가 대기 중입니다"}


@app.post("/test-user")
async def create_test_user():
    """(개발용) 테스트 유저 생성 API"""
    if settings.ENVIRONMENT != "development":
        return {"status": "error", "message": "개발 환경에서만 사용 가능합니다."}
    async with async_session_factory() as session:
        try:
            new_user = User(
                phone_number="010-1234-5678",
                real_name="이방원",
                gender=GenderType.MALE,
                birth_year=1950,
                role=UserRole.SUPER_ADMIN,
                tier=UserTier.B2C_PREMIUM,
                platform=PlatformType.ANDROID,
                daily_usage=0,
                last_usage_reset_at=datetime.now(),
                created_at=datetime.now(),
                last_active_at=datetime.now()
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return {"message": "축하드립니다, 첫 유저 생성 성공!", "user": new_user}
        except Exception as e:
            await session.rollback()
            logger.error("[test-user] 생성 실패: %s", e)
            detail = str(e) if settings.ENVIRONMENT == "development" else "테스트 유저 생성에 실패했습니다."
            return {"status": "error", "message": detail}
