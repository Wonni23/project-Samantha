# app/engine/base.py
"""
Gemini Engine 공통 베이스 클래스

[역할]
- Gemini 클라이언트/모델 초기화
- Context Caching 관리
- 토큰 사용량 추적

[사용법]
class ActorEngine(BaseGeminiEngine):
    def __init__(self, use_cache=None):
        super().__init__(
            model_name=settings.ACTOR_MODEL,
            system_prompt=ACTOR_SYSTEM_PROMPT,
            cache_key="actor",
            use_cache=use_cache,
        )
"""
from __future__ import annotations

import logging
from abc import ABC
from typing import Any, Dict, Optional

from google.genai import types

from app.core.config import settings
from app.integrations.llm.gemini_provider import get_cache_manager, get_genai_client

logger = logging.getLogger(__name__)


class BaseGeminiEngine(ABC):
    """
    Gemini Engine 공통 베이스 클래스

    [제공 기능]
    - 캐시/비캐시 모드 자동 분기
    - 토큰 사용량 추적 (last_token_usage)
    - 캐시 lazy initialization (_ensure_cache)
    """

    def __init__(
        self,
        model_name: str,
        system_prompt: str,
        cache_key: str,
        use_cache: Optional[bool] = None,
    ):
        """
        Gemini 모델 초기화

        Args:
            model_name: 사용할 모델 이름 (예: gemini-2.0-flash)
            system_prompt: 시스템 프롬프트
            cache_key: 캐시 식별자 (예: "actor")
            use_cache: Context Caching 사용 여부 (None이면 settings 따름)
        """
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.cache_key = cache_key
        self.use_cache = use_cache if use_cache is not None else settings.USE_CONTEXT_CACHE
        self._cache_name: Optional[str] = None

        # 공유 SDK 클라이언트 (캐시/비캐시 모두 사용)
        self.client = get_genai_client()

        # 마지막 호출의 토큰 사용량 저장
        # NOTE: 엔진이 싱글톤으로 사용되므로 동시 요청 환경에서는 last-writer-wins(요청 간 값 덮어쓰기)입니다.
        self.last_token_usage: Dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
        }

        engine_name = self.__class__.__name__
        logger.info(f"{engine_name} initialized (model={model_name}, cache={self.use_cache})")

    async def _ensure_cache(self) -> Optional[str]:
        """캐시 확보 (매 호출마다 만료 체크 — cache_manager 내부에서 hit/refresh/recreate 분기)"""
        if not self.use_cache:
            return None

        cache_manager = get_cache_manager()
        self._cache_name = await cache_manager.get_cache(
            cache_key=self.cache_key,
            system_instruction=self.system_prompt,
            model=self.model_name,
        )

        return self._cache_name

    def _update_token_usage(self, response: Any) -> None:
        """응답에서 토큰 사용량 추출 및 저장 (디버그용: 동시 요청에서는 last-writer-wins)"""
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            self.last_token_usage = {
                "prompt_tokens": getattr(usage, 'prompt_token_count', 0),
                "completion_tokens": getattr(usage, 'candidates_token_count', 0),
                "total_tokens": getattr(usage, 'total_token_count', 0),
                "cached_tokens": getattr(usage, 'cached_content_token_count', 0),
            }

    def _get_extra_generation_params(self) -> Dict[str, Any]:
        """서브클래스에서 오버라이드: 추가 GenerateContentConfig 파라미터"""
        return {}

    async def _call_gemini(self, input_context):
        """Gemini API 호출 (캐시/비캐시 자동 분기)"""
        cache_name = await self._ensure_cache() if self.use_cache else None

        params: Dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 1.0,
            **self._get_extra_generation_params(),
        }

        if cache_name:
            params["cached_content"] = cache_name
        else:
            params["system_instruction"] = self.system_prompt

        return await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=input_context,
            config=types.GenerateContentConfig(**params),
        )
