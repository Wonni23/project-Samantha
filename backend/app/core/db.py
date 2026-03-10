#/backend/core/db.py
import logging
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# HNSW 인덱스 설정 (벡터 검색 O(n) → O(log n) 최적화)
HNSW_CONFIG = {
    "m": 16,                # 노드당 최대 연결 수 (정확도↑ = 메모리↑)
    "ef_construction": 64,  # 빌드 시 탐색 범위 (정확도↑ = 빌드시간↑)
}

# [DB 연결 설정]
# 비동기 처리를 위해 postgresql -> postgresql+asyncpg로 변환
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL 환경변수가 설정되지 않았습니다. "
        ".env 파일을 확인하세요."
    )
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# [엔진 생성]
# SQL_ECHO=1 환경변수로 SQL 로그 활성화 (기본값: False)
SQL_ECHO = os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes")
engine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    future=True
)

# [세션 팩토리] (자판기 본체)
# 이 녀석이 요청이 올 때마다 세션을 하나씩 찍어냅니다.
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# async_session alias (main.py 호환)
async_session = async_session_factory


# [Dependency] (자판기 버튼)
# FastAPI 라우터에서 Depends(get_session)으로 사용할 함수입니다.
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            # 여기서 자동 커밋을 할 수도 있지만,
            # 보통은 라우터 내부에서 명시적으로 session.commit() 하는 것을 권장합니다.
        except Exception:
            await session.rollback() # 에러 나면 롤백
            raise
        finally:
            await session.close()    # 다 쓰면 반납


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """스크립트/테스트용 컨텍스트 매니저"""
    async with async_session_factory() as session:
        try:
            yield session
            # 스크립트에서 commit()을 직접 제어하도록 여기선 commit 안 함
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    데이터베이스 초기화: pgvector 확장 및 HNSW 인덱스 생성
    앱 시작 시 한 번 호출 (CREATE IF NOT EXISTS이므로 중복 실행 안전)
    """
    async with engine.begin() as conn:
        # 1. pgvector 확장 활성화
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # 2. life_legacies 테이블 존재 확인 (Alembic 미실행 환경 대응)
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'life_legacies');"
        ))
        table_exists = result.scalar()

        if not table_exists:
            logger.warning(
                "[DB] life_legacies 테이블이 아직 없습니다. "
                "인덱스 생성을 건너뜁니다. 'alembic upgrade head'를 실행하세요."
            )
            return

        # 3. HNSW 인덱스 생성 (코사인 거리용)
        await conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_life_legacies_embedding_hnsw
            ON life_legacies
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = {HNSW_CONFIG['m']}, ef_construction = {HNSW_CONFIG['ef_construction']});
        """))

        # 4. user_id 인덱스 (필터링 최적화)
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_life_legacies_user_id
            ON life_legacies (user_id);
        """))


async def close_db():
    """
    데이터베이스 연결 정리
    앱 종료 시 호출하여 연결 누수 방지
    """
    await engine.dispose()
