# backend/app/engine/session_store.py
"""
세션 저장소 — Protocol + Memory/Redis 구현

[구현체]
- MemorySessionStore: 개발/테스트용 (Dict 기반, 서버 재시작 시 소멸)
- RedisSessionStore: 프로덕션용 (TTL 기반, 분산 환경 지원)
"""
from __future__ import annotations

from typing import Dict, Optional, Protocol

from app.schemas.session_schema import SessionData


class SessionStore(Protocol):
    """
    세션 저장소 인터페이스

    구현체:
    - MemorySessionStore: 개발/테스트용
    - RedisSessionStore: 프로덕션용
    """

    async def get(self, user_id: int) -> Optional[SessionData]:
        """세션 조회"""
        ...

    async def set(self, user_id: int, data: SessionData) -> None:
        """세션 저장"""
        ...

    async def delete(self, user_id: int) -> None:
        """세션 삭제"""
        ...


class MemorySessionStore:
    """
    인메모리 세션 저장소

    용도: 개발/테스트 환경
    특징: 서버 재시작 시 데이터 소멸
    """

    def __init__(self) -> None:
        self._cache: Dict[int, SessionData] = {}

    async def get(self, user_id: int) -> Optional[SessionData]:
        return self._cache.get(user_id)

    async def set(self, user_id: int, data: SessionData) -> None:
        self._cache[user_id] = data

    async def delete(self, user_id: int) -> None:
        self._cache.pop(user_id, None)


class RedisSessionStore:
    """
    Redis 세션 저장소

    용도: 프로덕션 환경
    특징: TTL 기반 자동 만료, 분산 환경 지원
    """

    def __init__(self, redis_url: str, ttl: int = 300) -> None:
        """
        Args:
            redis_url: Redis 연결 URL
            ttl: 세션 만료 시간 (기본 5분 = 300초)
        """
        import redis.asyncio as redis

        self.redis = redis.from_url(redis_url)
        self.ttl = ttl

    def _key(self, user_id: int) -> str:
        """Redis 키 생성"""
        return f"session:{user_id}"

    async def get(self, user_id: int) -> Optional[SessionData]:
        """Redis에서 세션 조회. 연결 실패 시 예외 전파."""
        data = await self.redis.get(self._key(user_id))
        if data:
            return SessionData.model_validate_json(data)
        return None

    async def set(self, user_id: int, data: SessionData) -> None:
        """Redis에 세션 저장. 연결 실패 시 예외 전파."""
        await self.redis.setex(
            self._key(user_id), self.ttl, data.model_dump_json()
        )

    async def delete(self, user_id: int) -> None:
        """Redis에서 세션 삭제. 연결 실패 시 예외 전파."""
        await self.redis.delete(self._key(user_id))
