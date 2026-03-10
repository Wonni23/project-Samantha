# backend/app/engine/actor.py
"""
Actor Engine - Response Generator (Gemini 연동)

[역할]
ActorContext를 입력으로 받아 최종 응답 텍스트 생성:
- analysis-first 출력 (분석 → 응답)
- 5축 가중치 반영 말투/태도 결정
- RAG 결과 자연스럽게 반영
- 유저 감정에 맞는 응답 생성

[데이터 흐름]
Pipeline ──(ActorContext)──▶ ActorEngine(Gemini) ──▶ ActorResponse ──▶ TTS
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.genai import types

from app.core.config import settings
from app.core.exceptions import is_rate_limit_error, with_retry
from app.engine.base import BaseGeminiEngine
from app.engine.prompts import ACTOR_SYSTEM_PROMPT
from app.schemas.conversation_schema import ConversationTracker
from app.schemas.session_schema import AxisUpdates

logger = logging.getLogger(__name__)

ASSISTANT_NAME = "시아"


@dataclass
class ActorResponse:
    """Actor 응답 (텍스트 + 분석)"""
    response_text: str
    axis_updates: Optional[AxisUpdates] = None  # P1: 타입 검증됨
    conversation_tracker: Optional[ConversationTracker] = None  # P0: 타입 검증됨
    # analysis-first 출력에서 추출되는 분석 필드
    immediate_instruction: Optional[str] = None  # Director's note (자기 지시)
    user_emotion_refined: Optional[str] = None  # 정제된 감정 판단
    priority_refined: Optional[str] = None  # 정제된 priority


@dataclass
class ActorContext:
    """Actor 컨텍스트 — 1-LLM Direct 파이프라인의 메인 입력"""
    user_input_text: str

    # 대화 상태
    retrieved_memories: List[str] = field(default_factory=list)
    conversation_pacing: str = "PROBE"
    depth_level: int = 1
    turn_count: int = 1
    consecutive_probe_count: int = 0
    consecutive_absorb_count: int = 0
    user_emotion: str = "neutral"
    force_topic: Optional[str] = None
    next_move: str = ""

    # 세션에서 직접 가져오는 것
    persona_state: Dict[str, float] = field(default_factory=dict)
    user_title: str = "선생님"
    rapport_tier: str = "STRANGER"
    user_profile: Dict[str, Any] = field(default_factory=dict)
    persona_type: str = "balanced"
    persona_description: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_time_str: str = ""
    assistant_name: str = ASSISTANT_NAME


def build_multi_turn_contents(context: ActorContext) -> list:
    """ActorContext를 multi-turn Content 리스트로 변환 (implicit caching 최적화)

    구조:
      [대화 히스토리 (user/model 교차)] → prefix, implicit cache 재사용
      [현재 턴 컨텍스트 JSON (user)]    → 매 턴 변경되는 부분
    """
    contents: list = []

    # ── 1. 대화 히스토리 → multi-turn Content (cacheable prefix) ──
    history_turns = context.conversation_history[-settings.ACTOR_HISTORY_TURNS:]

    for turn in history_turns:
        role = turn.get("role", "unknown")
        text = turn.get("content", "")
        if not text:
            continue

        gemini_role = "user" if role == "user" else "model"

        # Gemini API 제약: role이 교차해야 함 → 연속 같은 role이면 병합
        if contents and contents[-1].role == gemini_role:
            prev_text = contents[-1].parts[0].text
            contents[-1] = types.Content(
                role=gemini_role,
                parts=[types.Part(text=f"{prev_text}\n{text}")]
            )
        else:
            contents.append(types.Content(
                role=gemini_role,
                parts=[types.Part(text=text)]
            ))

    # ── 2. 현재 턴: 컨텍스트 JSON + 사용자 입력 ──
    # ACTOR_SYSTEM_PROMPT가 참조하는 필드명 그대로 유지
    current_turn_data = {
        "identity_context": {
            "assistant_name": context.assistant_name,
            "user_title": context.user_title,
        },
        "user_context": {
            "title": context.user_title,
            "rapport_tier": context.rapport_tier,
            "persona_type": context.persona_type,
            "persona_description": context.persona_description,
            "persona_state": context.persona_state,
            "profile": context.user_profile,
        },
        "conversation_context": {
            "pacing": context.conversation_pacing,
            "depth_level": context.depth_level,
            "turn_count": context.turn_count,
            "consecutive_probe_count": context.consecutive_probe_count,
            "consecutive_absorb_count": context.consecutive_absorb_count,
            "next_move": context.next_move,
        },
        "env_context": {"current_time_str": context.current_time_str},
        "memory_operations": context.retrieved_memories if context.retrieved_memories else None,
        "analysis_context": {
            "user_emotion": context.user_emotion,
            "force_topic": context.force_topic,
        },
        "user_input_text": context.user_input_text,
    }

    current_json = json.dumps(current_turn_data, ensure_ascii=False, indent=2)

    # 마지막 Content가 user이면 model ack 삽입 (API 교차 규칙)
    if contents and contents[-1].role == "user":
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text="(acknowledged)")]
        ))

    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=current_json)]
    ))

    logger.info(
        "=== ACTOR MULTI-TURN CONTENTS === content_count=%d, history_turns=%d, profile_keys=%s, memories=%d",
        len(contents),
        len(history_turns),
        list(context.user_profile.keys()),
        len(context.retrieved_memories),
    )

    return contents


class ActorEngine(BaseGeminiEngine):
    """
    Actor Engine - Gemini 기반 응답 생성

    [사용법]
    actor = ActorEngine()
    response = await actor.generate(context)
    print(actor.last_token_usage)  # 토큰 사용량 확인

    [Context Caching]
    USE_CONTEXT_CACHE=true 시 시스템 프롬프트 캐싱으로 75% 토큰 절감
    """

    def __init__(self, use_cache: Optional[bool] = None):
        """
        Gemini 모델 초기화

        Args:
            use_cache: Context Caching 사용 여부 (None이면 settings 따름)
        """
        super().__init__(
            model_name=settings.ACTOR_MODEL,
            system_prompt=ACTOR_SYSTEM_PROMPT,
            cache_key="actor",
            use_cache=use_cache,
        )

    async def generate(self, context: ActorContext) -> ActorResponse:
        """
        ActorContext 기반 응답 생성 (ACTOR_SYSTEM_PROMPT 사용)

        Args:
            context: ActorContext

        Returns:
            ActorResponse: 응답 + axis_updates
        """
        input_context = self._build_input_context(context)

        try:
            response = await with_retry(
                lambda: self._call_gemini(input_context),
            )
        except Exception as e:
            logger.error(f"ActorEngine API call failed: {e}")
            return ActorResponse(
                response_text=self._get_fallback_response(
                    "neutral", context.user_title, "neutral"
                )
            )

        self._update_token_usage(response)

        response_text = response.text
        raw_response = response_text.strip() if response_text else ""
        if not raw_response:
            logger.warning("ActorEngine returned empty response")
            return ActorResponse(
                response_text=self._get_fallback_response(
                    "neutral", context.user_title, "neutral"
                )
            )
        logger.info(f"=== ACTOR RAW RESPONSE ===\n{raw_response}\n=========================")

        return self._parse_actor_response(raw_response, context.user_title)

    async def generate_stream(
        self, context: ActorContext
    ) -> AsyncGenerator[str, None]:
        """스트리밍 응답 생성"""
        input_context = self._build_input_context(context)

        max_retries = settings.API_MAX_RETRIES
        last_error = None

        for attempt in range(max_retries):
            yielded_any = False
            try:
                async for chunk_text in self._stream_chunks(input_context):
                    yielded_any = True
                    yield chunk_text

                if not yielded_any:
                    logger.warning("ActorEngine stream returned 0 chunks")
                    yield self._get_fallback_response(
                        "neutral", context.user_title, "neutral"
                    )
                return

            except Exception as e:
                last_error = e

                if yielded_any:
                    # 이미 부분 전송된 상태 → 재시도하면 중복 콘텐츠 발생
                    logger.warning(f"ActorEngine stream error after partial yield: {e}")
                    return

                if is_rate_limit_error(e):
                    wait_time = settings.API_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"ActorEngine stream error: {e}")
                yield self._get_fallback_response("neutral", context.user_title, "neutral")
                return

        logger.error(f"ActorEngine stream failed after {max_retries} retries: {last_error}")
        yield self._get_fallback_response("neutral", context.user_title, "neutral")

    async def _stream_chunks(self, input_context) -> AsyncGenerator[str, None]:
        """스트리밍 청크 생성 (캐시/비캐시 자동 분기, 마지막 chunk에서 토큰 사용량 추적)"""
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

        async for chunk in await self.client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=input_context,
            config=types.GenerateContentConfig(**params),
        ):
            if chunk.text:
                yield chunk.text
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                self._update_token_usage(chunk)

    def _build_input_context(self, context: ActorContext) -> list:
        """ActorContext를 multi-turn Content 리스트로 변환 (implicit caching 최적화)"""
        return build_multi_turn_contents(context)

    def _get_extra_generation_params(self) -> Dict[str, Any]:
        return {
            "max_output_tokens": settings.ACTOR_MAX_TOKENS,
            "thinking_config": types.ThinkingConfig(
                thinking_level=settings.ACTOR_THINKING_LEVEL,
            ),
        }

    def _parse_actor_response(self, raw_response: str, user_title: str) -> ActorResponse:
        """
        Actor 응답에서 JSON 파싱하여 ActorResponse 생성

        Args:
            raw_response: Gemini 원본 응답 (JSON 또는 텍스트)
            user_title: fallback용 유저 호칭

        Returns:
            ActorResponse: 파싱된 응답
        """
        # 빈 응답 검증
        if not raw_response or not raw_response.strip():
            logger.warning("Empty response from Actor, using fallback")
            return ActorResponse(
                response_text=self._get_fallback_response("neutral", user_title, "neutral")
            )

        # JSON 블록 추출 (```json ... ``` 또는 { ... })
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        elif raw_response.strip().startswith(('{', '[')):
            json_str = raw_response.strip()
        else:
            # JSON이 아니면 텍스트 그대로 반환 (단, 유효한 텍스트인지 확인)
            if len(raw_response.strip()) < 5:
                logger.warning("Actor response too short, using fallback")
                return ActorResponse(
                    response_text=self._get_fallback_response("neutral", user_title, "neutral")
                )
            logger.warning("Actor response is not JSON, using as plain text")
            return ActorResponse(response_text=raw_response)

        try:
            data = json.loads(json_str)
            # 배열 래핑 언래핑: [{...}] → {...}
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    logger.warning("Actor response is empty array or non-dict element, using fallback")
                    return ActorResponse(
                        response_text=self._get_fallback_response("neutral", user_title, "neutral")
                    )
            response_text = data.get("response_text", "")

            # response_text 빈 값 검증
            if not response_text or not response_text.strip():
                logger.warning("Empty response_text in JSON, using fallback")
                return ActorResponse(
                    response_text=self._get_fallback_response("neutral", user_title, "neutral")
                )

            # analysis-first 구조: analysis 블록에서 추출 (하위 호환: top-level도 확인)
            analysis = data.get("analysis", {}) or {}

            # axis_updates: Dict → AxisUpdates 변환 (P1: 구조 검증)
            axis_updates_raw = analysis.get("axis_updates") or data.get("axis_updates")
            axis_updates = None
            if axis_updates_raw:
                try:
                    axis_updates = AxisUpdates(**axis_updates_raw)
                    logger.debug(f"axis_updates parsed: {axis_updates.extract_deltas()}")
                except (TypeError, ValueError) as e:
                    logger.error(f"axis_updates validation failed: {e}, falling back to None")

            # conversation_tracker: Dict → ConversationTracker 변환 (P0: 구조 검증)
            tracker_raw = analysis.get("conversation_tracker") or data.get("conversation_tracker")
            conversation_tracker = None
            if tracker_raw:
                try:
                    conversation_tracker = ConversationTracker(**tracker_raw)
                    logger.debug(f"conversation_tracker parsed: {conversation_tracker}")
                except (TypeError, ValueError) as e:
                    logger.error(f"conversation_tracker validation failed: {e}, falling back to None")

            return ActorResponse(
                response_text=response_text,
                axis_updates=axis_updates,
                conversation_tracker=conversation_tracker,
                immediate_instruction=analysis.get("immediate_instruction"),
                user_emotion_refined=analysis.get("user_emotion_refined"),
                priority_refined=analysis.get("priority_refined"),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Actor JSON: {e}")
            # raw_response가 유효한 텍스트인지 검증
            if len(raw_response) > 10 and not raw_response.strip().startswith(("{", "[")):
                return ActorResponse(response_text=raw_response)
            return ActorResponse(
                response_text=self._get_fallback_response("neutral", user_title, "neutral")
            )

    def _get_fallback_response(
        self, user_emotion: str, user_title: str, intent: str = "neutral"
    ) -> str:
        """
        API 에러 시 의도 기반 fallback 응답 반환

        원칙:
        1. "해줄게요", "드릴게요" 표현 금지 (prompts.py 지침 준수)
        2. 정보/이야기 요청 시 재시도 유도 (빈 약속 방지)
        3. 감정적 지지는 즉시 제공
        """
        # 정보/이야기 요청 감지 (intent 기반)
        info_intents = ["question", "story", "explain", "tell", "information", "ask", "request"]
        if intent and any(kw in intent.lower() for kw in info_intents):
            return (
                f"{user_title}, 아... 지금 제 머리가 잠깐 멈춰버렸어요. "
                f"다시 한 번 말씀해 주시겠어요?"
            )

        # 감정 기반 fallback (수정: "해줄게요" 표현 제거)
        fallback_responses = {
            "lonely": f"{user_title}, 외로우셨어요? 저 여기 있어요. 같이 이야기해요.",
            "happy": f"와~ {user_title} 기분 좋으신 거 저도 느껴져요!",
            "sad": f"{user_title}... 마음이 안 좋으신가요? 저한테 말씀해 주세요.",
            "angry": f"{user_title}, 화나셨어요? 무슨 일인지 들려주세요.",
            "nostalgic": "그때 생각이 나시는군요. 더 들려주세요.",
            "neutral": f"{user_title}~ 네, 듣고 있어요. 말씀해 주세요.",
        }
        return fallback_responses.get(
            user_emotion, f"{user_title}, 네~ 저 사만다예요."
        )


# 싱글톤 인스턴스
_actor_engine: Optional[ActorEngine] = None


def get_actor_engine() -> ActorEngine:
    """ActorEngine 싱글톤 반환"""
    global _actor_engine
    if _actor_engine is None:
        _actor_engine = ActorEngine()
    return _actor_engine
