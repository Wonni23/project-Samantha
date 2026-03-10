# app/core/exceptions.py
"""
Samanda 도메인 예외 클래스 계층 구조

[계층 구조]
SamandaException (기본)
├── LLMException (LLM 관련)
│   ├── RateLimitException
│   └── TokenLimitException
├── RAGException (RAG 관련)
│   ├── EmbeddingException
│   └── SearchException
├── TTSException (TTS 관련)
├── STTException (STT 관련)
└── SessionException (세션 관련)
    └── SessionNotFoundException
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional, TypeVar

from fastapi import HTTPException, status


# ==================== HTTP 예외 (API용) ====================


class AuthError:
    """인증 과정에서 발생하는 공통 예외 모음"""

    # 401: 자격 증명 실패 (토큰 없음, 서명 불일치 등)
    CREDENTIALS_INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명이 유효하지 않거나 누락되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 401: 토큰 만료
    TOKEN_EXPIRED = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="토큰의 유효 기간이 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 404: 유저 없음 (탈퇴했거나 잘못된 ID)
    USER_NOT_FOUND = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="해당 사용자를 찾을 수 없습니다."
    )

    # 400: 이미 존재하는 이메일
    EMAIL_ALREADY_EXISTS = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="이미 존재하는 이메일입니다."
    )

    # 400: 잘못된 소셜 로그인 요청
    SOCIAL_LOGIN_FAILED = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="소셜 로그인 처리에 실패했습니다."
    )


# ==================== 도메인 예외 (내부용) ====================


class SamandaException(Exception):
    """Samanda 기본 예외"""

    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)


# ==================== LLM 관련 예외 ====================


class LLMException(SamandaException):
    """LLM API 관련 예외"""

    def __init__(self, message: str, code: str = "LLM_ERROR"):
        super().__init__(message, code)


class RateLimitException(LLMException):
    """API Rate Limit 초과"""

    def __init__(self, message: str = "API 요청 한도 초과"):
        super().__init__(message, "RATE_LIMIT")


class TokenLimitException(LLMException):
    """토큰 제한 초과"""

    def __init__(self, message: str = "토큰 제한 초과"):
        super().__init__(message, "TOKEN_LIMIT")


# ==================== RAG 관련 예외 ====================


class RAGException(SamandaException):
    """RAG 시스템 관련 예외"""

    def __init__(self, message: str, code: str = "RAG_ERROR"):
        super().__init__(message, code)


class EmbeddingException(RAGException):
    """임베딩 생성 실패"""

    def __init__(self, message: str = "임베딩 생성 실패"):
        super().__init__(message, "EMBEDDING_ERROR")


class SearchException(RAGException):
    """검색 실패"""

    def __init__(self, message: str = "검색 실패"):
        super().__init__(message, "SEARCH_ERROR")


# ==================== TTS 관련 예외 ====================


class TTSException(SamandaException):
    """TTS 변환 관련 예외"""

    def __init__(self, message: str = "음성 변환에 실패했습니다", code: str = "TTS_ERROR"):
        super().__init__(message, code)


# ==================== STT 관련 예외 ====================


class STTException(SamandaException):
    """STT 변환 관련 예외"""

    def __init__(self, message: str = "음성 인식에 실패했습니다", code: str = "STT_ERROR"):
        super().__init__(message, code)


# ==================== 세션 관련 예외 ====================


class SessionException(SamandaException):
    """세션 관련 예외"""

    def __init__(self, message: str, code: str = "SESSION_ERROR"):
        super().__init__(message, code)


class SessionNotFoundException(SessionException):
    """세션을 찾을 수 없음"""

    def __init__(self, session_id: str):
        super().__init__(f"세션을 찾을 수 없음: {session_id}", "SESSION_NOT_FOUND")
        self.session_id = session_id


# ==================== 유틸리티 함수 ====================


def is_rate_limit_error(e: Exception) -> bool:
    """Rate Limit 에러인지 확인 (타입 기반 우선, 문자열 fallback)"""
    # 1) 자체 예외
    if isinstance(e, RateLimitException):
        return True

    # 2) Google GenAI SDK: ClientError(code=429)
    try:
        from google.genai.errors import ClientError
        if isinstance(e, ClientError) and getattr(e, "code", None) == 429:
            return True
    except ImportError:
        pass

    # 3) Google API Core: TooManyRequests / ResourceExhausted
    try:
        from google.api_core.exceptions import TooManyRequests, ResourceExhausted
        if isinstance(e, (TooManyRequests, ResourceExhausted)):
            return True
    except ImportError:
        # google-api-core는 선택적 의존성이므로, 미설치 시 Rate Limit 판별을 이 경로에서는 건너뛰고
        # 아래의 다른 fallback 로직(status_code / code 기반 판별)을 사용한다.
        pass

    # 4) 기타 HTTP 라이브러리 fallback: status_code 속성 확인
    status = getattr(e, "status_code", None) or getattr(e, "code", None)
    if status == 429:
        return True

    return False


T = TypeVar("T")
_logger = logging.getLogger(__name__)


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    on_retry: Optional[Callable[[int, float], None]] = None,
) -> T:
    """
    지수 백오프 재시도

    Args:
        fn: 실행할 비동기 함수
        max_retries: 최대 재시도 횟수 (None이면 settings.API_MAX_RETRIES)
        base_delay: 기본 대기 시간 (None이면 settings.API_RETRY_BASE_DELAY)
        on_retry: 재시도 시 콜백 (attempt, wait_time)

    Returns:
        fn의 반환값

    Raises:
        RateLimitException: 모든 재시도 실패 시
        Exception: Rate limit 외의 예외는 즉시 재발생
    """
    from app.core.config import settings

    retries = max_retries if max_retries is not None else settings.API_MAX_RETRIES
    delay = base_delay if base_delay is not None else settings.API_RETRY_BASE_DELAY
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            last_error = e

            if is_rate_limit_error(e):
                wait_time = delay * (2 ** attempt)  # 1, 2, 4초 (지수 백오프)

                if on_retry:
                    on_retry(attempt + 1, wait_time)
                else:
                    _logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait_time}s..."
                    )

                await asyncio.sleep(wait_time)
                continue

            # Rate limit 외 예외는 즉시 재발생
            raise

    # 모든 재시도 실패
    raise RateLimitException(
        f"API 요청 한도 초과 - {retries}회 재시도 후 실패: {last_error}"
    )
