# app/core/config.py
import os
from datetime import datetime
from typing import List
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Samantha")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # LLM 모델 설정
    EXTRACT_MODEL: str = os.getenv("EXTRACT_MODEL", "gemini-2.5-flash-lite")  # extraction/summary용
    ACTOR_MODEL: str = os.getenv("ACTOR_MODEL", "gemini-3-flash-preview")  # Actor용
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    # API 키 (필수 - 서버 시작 시 검증)
    # GEMINI_API_KEY 우선, 없으면 GOOGLE_API_KEY fallback (하위 호환)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_TTS_API_KEY: str = os.getenv("GOOGLE_TTS_API_KEY", "")

    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis / 세션 설정
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "300"))  # 세션 타임아웃 (기본 5분)

    # S3/MinIO 설정
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9005")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "samantha-bucket")

    # JWT 보안 설정
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # OAuth 클라이언트 키
    KAKAO_CLIENT_ID: str = os.getenv("KAKAO_CLIENT_ID", "")
    KAKAO_CLIENT_SECRET: str = os.getenv("KAKAO_CLIENT_SECRET", "")
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Socket.IO 설정
    SOCKET_PING_INTERVAL: int = 25
    SOCKET_PING_TIMEOUT: int = 5
    SOCKET_IDLE_TIMEOUT_MINUTES: int = 30
    SOCKET_IDLE_CHECK_INTERVAL: int = 60

    # 대화 히스토리 설정
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "20"))  # 세션 저장 최대 턴
    ACTOR_HISTORY_TURNS: int = int(os.getenv("ACTOR_HISTORY_TURNS", "20"))  # Actor용

    # Actor 토큰 제한 설정
    ACTOR_MAX_TOKENS: int = int(os.getenv("ACTOR_MAX_TOKENS", "16384"))  # 일반 응답 (JSON 포함)
    ACTOR_THINKING_LEVEL: str = os.getenv("ACTOR_THINKING_LEVEL", "low")  # gemini-3-flash: minimal|low|medium|high

    # Context Caching 설정 (gemini-3-flash-preview에서 explicit caching 확인됨)
    USE_CONTEXT_CACHE: bool = os.getenv("USE_CONTEXT_CACHE", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 캐시 TTL (기본 1시간)
    CACHE_REFRESH_BEFORE_SECONDS: int = int(os.getenv("CACHE_REFRESH_BEFORE_SECONDS", "300"))  # 만료 전 갱신 (5분)

    # RAG 설정
    RAG_VECTOR_WEIGHT: float = float(os.getenv("RAG_VECTOR_WEIGHT", "0.3"))  # 벡터 유사도 가중치 (Grid Search 최적화: 0.3)
    RAG_KEYWORD_WEIGHT: float = float(os.getenv("RAG_KEYWORD_WEIGHT", "0.7"))  # 키워드 매칭 가중치 (Grid Search 최적화: 0.7)
    RAG_IMPORTANCE_WEIGHT: float = float(os.getenv("RAG_IMPORTANCE_WEIGHT", "0.15"))  # importance 보너스
    RAG_DUPLICATE_THRESHOLD: float = float(os.getenv("RAG_DUPLICATE_THRESHOLD", "0.15"))  # 중복 판단 코사인 거리 (0.15 = 85% 유사)
    RAG_VECTOR_THRESHOLD: float = float(os.getenv("RAG_VECTOR_THRESHOLD", "0.65"))  # 벡터 검색 임계값 (Grid Search 최적화: 0.65)
    RAG_MAX_IMPORTANCE: int = int(os.getenv("RAG_MAX_IMPORTANCE", "5"))  # importance 상한값

    # API 재시도 설정
    API_MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))
    API_RETRY_BASE_DELAY: float = float(os.getenv("API_RETRY_BASE_DELAY", "1.0"))

    # 텍스트 제한
    EMBEDDING_TEXT_MAX_LENGTH: int = int(os.getenv("EMBEDDING_TEXT_MAX_LENGTH", "8000"))

    # TTS 설정
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "openai")  # "openai" | "google"
    TTS_DEFAULT_VOICE: str = os.getenv("TTS_DEFAULT_VOICE", "nova")
    TTS_DEFAULT_SPEED: float = float(os.getenv("TTS_DEFAULT_SPEED", "1.0"))

    # STT Hallucination 방어 임계값 (시니어 음성 특성 반영: 작은 목소리, 불명확 발음 허용)
    STT_NO_SPEECH_PROB_THRESHOLD: float = float(os.getenv("STT_NO_SPEECH_PROB_THRESHOLD", "0.8"))
    STT_AVG_LOGPROB_THRESHOLD: float = float(os.getenv("STT_AVG_LOGPROB_THRESHOLD", "-1.5"))

    # 보안 설정
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() == "true"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        # 환경 변수가 있으면 최우선 적용
        raw_origins = os.getenv("CORS_ORIGINS")
        if raw_origins:
            origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
            if self.FORCE_HTTPS:
                return [o for o in origins if o.startswith("https://")]
            return origins

        # 비프로덕션 환경 기본값
        if self.ENVIRONMENT != "production":
            # HTTPS 강제가 활성화된 경우 HTTPS URL만 허용
            if self.FORCE_HTTPS:
                return ["https://localhost:3000", "https://localhost:8080", "https://localhost:8443"]
            else:
                return ["http://localhost:3000", "http://localhost:8080", 
                       "https://localhost:3000", "https://localhost:8080",
                       "https://localhost:8443"]

        # 프로덕션에서 설정이 없으면 안전을 위해 허용 안 함
        return []

    def validate_required(self) -> None:
        """필수 환경 변수 검증 - 서버 시작 시 호출"""
        missing = []
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")

        # 프로덕션 전용: S3 기본 자격증명 차단
        if self.ENVIRONMENT == "production":
            if self.S3_ACCESS_KEY == "minioadmin":
                missing.append("S3_ACCESS_KEY (프로덕션에서 기본값 사용 불가)")
            if self.S3_SECRET_KEY == "minioadmin":
                missing.append("S3_SECRET_KEY (프로덕션에서 기본값 사용 불가)")

        if missing:
            raise ValueError(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing)}")


settings = Settings()

# ── 시간대 유틸 ──
_KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    """프로젝트 표준 현재 시각 (Asia/Seoul)."""
    return datetime.now(_KST)
