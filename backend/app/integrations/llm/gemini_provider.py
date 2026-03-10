# app/integrations/llm/gemini.py
"""
Google Gemini 인터페이스 구현 + Context Cache 관리
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from app.integrations.llm.base import BaseLLMProvider, GenerationConfig
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Shared genai.Client (모듈 레벨 싱글톤)
# =============================================================================

_genai_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """genai.Client 싱글톤 반환 (커넥션 풀 공유)"""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _genai_client


# =============================================================================
# Context Cache Manager
# =============================================================================


@dataclass
class CacheEntry:
    """캐시 엔트리 정보"""

    cache_name: str  # Gemini 캐시 리소스 이름
    prompt_hash: str  # 프롬프트 해시 (변경 감지용)
    created_at: datetime
    expires_at: datetime
    model: str


class GeminiCacheManager:
    """
    Gemini Context Cache Manager

    [효과]
    - 시스템 프롬프트 반복 전송 제거

    [사용법]
    cache_manager = get_cache_manager()  # 모듈 레벨 싱글톤
    actor_cache = await cache_manager.get_cache("actor", ACTOR_SYSTEM_PROMPT, model)
    """

    def __init__(self, client: genai.Client) -> None:
        self.client = client
        self._caches: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        logger.info("GeminiCacheManager initialized")

    def _compute_hash(self, content: str) -> str:
        """프롬프트 해시 계산 (변경 감지용)"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get_cache(
        self,
        cache_key: str,
        system_instruction: str,
        model: str,
    ) -> Optional[str]:
        """
        캐시 조회 또는 생성

        Args:
            cache_key: 캐시 키 (예: "actor")
            system_instruction: 시스템 프롬프트
            model: Gemini 모델명

        Returns:
            캐시 이름 (None이면 캐시 생성 실패)
        """
        prompt_hash = self._compute_hash(system_instruction)

        # Phase 1: Lock 내에서 상태 확인만 수행 (빠른 체크)
        action_needed = None  # "delete", "refresh", "create", or None (cache hit)
        cache_name_to_delete = None
        entry_to_refresh = None

        async with self._lock:
            if cache_key in self._caches:
                entry = self._caches[cache_key]
                now = datetime.now(timezone.utc)

                if entry.prompt_hash != prompt_hash:
                    # 프롬프트 변경 → 삭제 후 재생성 필요
                    action_needed = "delete"
                    cache_name_to_delete = entry.cache_name
                    del self._caches[cache_key]
                elif entry.expires_at - now < timedelta(seconds=settings.CACHE_REFRESH_BEFORE_SECONDS):
                    # 만료 임박 → 갱신 필요
                    action_needed = "refresh"
                    entry_to_refresh = entry
                else:
                    # 캐시 히트
                    return entry.cache_name
            else:
                action_needed = "create"

        # Phase 2: Lock 외부에서 비동기 작업 수행 (경쟁 조건 최소화)
        if action_needed == "delete":
            logger.info(f"Prompt changed for {cache_key}, recreating cache")
            await self._delete_cache(cache_name_to_delete)
            return await self._create_cache(cache_key, system_instruction, model, prompt_hash)

        elif action_needed == "refresh":
            logger.info(f"Cache expiring soon for {cache_key}, refreshing")
            await self._refresh_cache(cache_key, entry_to_refresh)
            async with self._lock:
                return self._caches.get(cache_key, entry_to_refresh).cache_name

        elif action_needed == "create":
            return await self._create_cache(cache_key, system_instruction, model, prompt_hash)

        return None

    async def _create_cache(
        self,
        cache_key: str,
        system_instruction: str,
        model: str,
        prompt_hash: str,
    ) -> Optional[str]:
        """신규 캐시 생성 (Lock 외부에서 호출)"""
        try:
            # API 호출은 Lock 외부에서 수행
            cache = await self.client.aio.caches.create(
                model=model,
                config=types.CreateCachedContentConfig(
                    display_name=f"samantha_{cache_key}_cache",
                    system_instruction=system_instruction,
                    ttl=f"{settings.CACHE_TTL_SECONDS}s",
                ),
            )

            now = datetime.now(timezone.utc)
            new_entry = CacheEntry(
                cache_name=cache.name,
                prompt_hash=prompt_hash,
                created_at=now,
                expires_at=now + timedelta(seconds=settings.CACHE_TTL_SECONDS),
                model=model,
            )

            # 상태 업데이트는 Lock 내에서 수행 (double-check)
            stale_name: Optional[str] = None
            async with self._lock:
                if cache_key in self._caches:
                    # 다른 요청이 먼저 생성함 → 방금 만든 캐시는 Lock 밖에서 삭제
                    stale_name = cache.name
                    winner_name = self._caches[cache_key].cache_name
                else:
                    self._caches[cache_key] = new_entry

            if stale_name:
                await self._delete_cache(stale_name)
                return winner_name

            logger.info(f"Cache created: key={cache_key}, name={cache.name}")
            return cache.name

        except Exception as e:
            logger.error(f"Failed to create cache for {cache_key}: {e}")
            return None

    async def _refresh_cache(self, cache_key: str, entry: CacheEntry) -> None:
        """캐시 TTL 갱신 (Lock 외부에서 호출)"""
        try:
            new_expire = datetime.now(timezone.utc) + timedelta(
                seconds=settings.CACHE_TTL_SECONDS
            )
            # API 호출은 Lock 외부에서 수행
            await self.client.aio.caches.update(
                name=entry.cache_name,
                config=types.UpdateCachedContentConfig(expire_time=new_expire),
            )

            # 상태 업데이트는 Lock 내에서 수행 (새 객체 생성)
            async with self._lock:
                if cache_key in self._caches:
                    updated_entry = CacheEntry(
                        cache_name=entry.cache_name,
                        prompt_hash=entry.prompt_hash,
                        created_at=entry.created_at,
                        expires_at=new_expire,
                        model=entry.model,
                    )
                    self._caches[cache_key] = updated_entry

            logger.info(f"Cache TTL refreshed: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to refresh cache {cache_key}: {e}")
            # 갱신 실패 시 캐시 삭제 후 재생성 유도
            async with self._lock:
                self._caches.pop(cache_key, None)

    async def _delete_cache(self, cache_name: str) -> None:
        """캐시 삭제"""
        try:
            await self.client.aio.caches.delete(name=cache_name)
            logger.info(f"Cache deleted: {cache_name}")
        except Exception as e:
            logger.error(f"Failed to delete cache {cache_name}: {e}")

    async def cleanup(self) -> None:
        """모든 캐시 정리 (애플리케이션 종료 시)"""
        for key, entry in list(self._caches.items()):
            await self._delete_cache(entry.cache_name)
        self._caches.clear()
        logger.info("All caches cleaned up")



# 싱글톤 인스턴스
_cache_manager: Optional[GeminiCacheManager] = None


async def warm_up_connections() -> None:
    """서버 시작 시 Gemini API HTTP/2 연결 풀 사전 초기화.

    Context Cache warm-up이 이미 API 호출을 하므로 연결이 warm 되지만,
    USE_CONTEXT_CACHE=false일 때를 대비한 독립 warm-up.
    """
    client = get_genai_client()
    try:
        await client.aio.models.generate_content(
            model=settings.ACTOR_MODEL,
            contents="ping",
            config=types.GenerateContentConfig(max_output_tokens=1, temperature=0.0),
        )
    except Exception as e:
        logger.warning("Connection warm-up failed (non-critical): %s", e)


def get_cache_manager() -> GeminiCacheManager:
    """CacheManager 싱글톤 반환"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = GeminiCacheManager(client=get_genai_client())
    return _cache_manager


# =============================================================================
# Gemini Provider
# =============================================================================


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Gemini 초기화

        Args:
            model_name: Gemini 모델 이름 (설정에서 기본값 사용)
        """
        self.client = get_genai_client()
        self.model_name = model_name or settings.EXTRACT_MODEL

    def _convert_config(self, config: Optional[GenerationConfig]) -> types.GenerateContentConfig:
        """설정을 Gemini 설정으로 변환"""
        if not config:
            config = GenerationConfig()

        return types.GenerateContentConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            top_p=config.top_p,
            top_k=config.top_k
        )
    
    async def generate_text(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        response_mime_type: Optional[str] = None
    ) -> str:
        """프롬프트로부터 텍스트 생성"""
        try:
            gemini_config = self._convert_config(config)

            # response_mime_type 추가 (JSON 형식 강제)
            if response_mime_type:
                gemini_config.response_mime_type = response_mime_type

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=gemini_config
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini 생성 오류: {e}", exc_info=True)
            raise
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """히스토리와 함께 채팅 응답 생성"""
        try:
            # 메시지를 Gemini 형식으로 변환
            gemini_contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            # 설정 생성
            gemini_config = self._convert_config(config)
            if system_prompt:
                gemini_config.system_instruction = system_prompt

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=gemini_contents,
                config=gemini_config
            )

            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini 채팅 오류: {e}", exc_info=True)
            raise
    
    async def generate_structured(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> Dict[str, Any]:
        """구조화된 JSON 출력 생성"""
        try:
            if not config:
                config = GenerationConfig(temperature=0.3)

            # JSON 형식 강제
            response_text = await self.generate_text(
                prompt,
                config,
                response_mime_type="application/json"
            )

            # 마크다운 JSON 블록이 있으면 제거
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            data = json.loads(response_text)
            # Gemini thinking OFF 시 [{...}] 배열 래핑 대응
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    raise ValueError(f"Gemini returned empty array or non-dict element: {response_text[:200]}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"전체 응답 ({len(response_text)} chars):\n{response_text}")
            raise ValueError(f"Gemini 응답에서 JSON 파싱 실패: {e}")
        except Exception as e:
            logger.error(f"Gemini 구조화된 생성 오류: {e}", exc_info=True)
            raise
