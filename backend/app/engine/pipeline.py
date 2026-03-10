# backend/app/engine/pipeline.py
"""
Samantha Direct 파이프라인 — 오케스트레이션 + 헬퍼 함수

[역할]
1. SamanthaPipeline: Direct 파이프라인 (run, run_stream, run_stream_with_voice)
2. 헬퍼 함수: 프로필 검색, 키워드 추출, pacing/depth 가드레일
3. 팩토리: create_pipeline

[데이터 흐름]
User → Rule-based Router → Always RAG → Actor(analysis-first) → Response

[관련 모듈]
- session_store.py: 세션 저장소 (Protocol + Memory/Redis 구현)
- conversation.py: 세션 관리, Legacy/Profile 영속화, txt 내보내기
"""
from __future__ import annotations

import logging
import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.engine.memory import MemoryEngine, get_kiwi, get_memory_engine
from app.engine.session_store import MemorySessionStore, RedisSessionStore, SessionStore
from app.engine.conversation import ConversationPipeline
from app.schemas.conversation_schema import (
    ConversationPacing,
    ConversationTracker,
    ConversationContext,
)
from app.schemas.session_schema import AxisUpdates, PERSONA_PRESETS, SessionData
from app.core.config import now_kst
from app.core.exceptions import RateLimitException, SamandaException

logger = logging.getLogger(__name__)

# ============ Kiwi 싱글톤 (서버 시작 시 초기화) ============
# 대화 TTFT 최적화: 첫 대화에서 Kiwi 로딩 대기 제거
_kiwi = get_kiwi()


# ============ Profile Search Helper ============


def _flatten_dict(d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
    """Nested Dict를 Flat하게 변환"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def search_profile_by_keywords(
    user_profile: Dict[str, Any],
    keywords: List[str],
    max_results: int = 5,
) -> List[str]:
    """
    여러 키워드로 user_profile 검색

    Args:
        user_profile: Nested Dict 구조의 프로필
        keywords: 검색 키워드 리스트
        max_results: 최대 결과 개수

    Returns:
        검색 결과 문자열 리스트 (Actor용)
    """
    if not keywords or not user_profile:
        return []

    results = []
    seen_keys = set()

    # Flatten하여 검색
    flat = _flatten_dict(user_profile)

    # 유효한 키워드만 필터링
    valid_keywords = [k for k in keywords if k and k.strip()]

    for keyword in valid_keywords:
        keyword_lower = keyword.lower()

        for key, value in flat.items():
            if key in seen_keys:
                continue

            if keyword_lower in key.lower() or keyword_lower in str(value).lower():
                results.append(f"{key}: {value}")
                seen_keys.add(key)

            if len(results) >= max_results:
                return results

    return results


# ============ Direct Pipeline Helpers ============


def extract_profile_keywords_simple(user_text: str) -> List[str]:
    """Kiwi로 고유명사(NNP) + 일반명사(NNG) 추출하여 profile 검색 키워드로 사용"""
    tokens = _kiwi.tokenize(user_text)
    keywords = []
    for token in tokens:
        if token.tag == "NNP" and len(token.form) >= 1:
            keywords.append(token.form)
        elif token.tag == "NNG" and len(token.form) >= 2:
            keywords.append(token.form)
    return keywords[:5]



def compute_depth_level_simple(
    actor_depth: int,
    current_turn_count: int,
) -> int:
    """
    규칙 기반 depth_level: Condition C (기본 진행)만 강제

    원본 의도 (Condition C):
    - Turn 1: depth_level=1 (FACT - 사실 수집)
    - Turn 2: depth_level=2 (EMOTION - 감정 탐색)
    - Turn 3+: depth_level=2 유지 (억지로 깊게 안 파고듦)

    특수 케이스 (LLM 판단 유지):
    - Condition A: 과거/특정 인물 언급 → depth=3 (LLM이 감지)
    - Condition B: depth=2에서 3턴+ 정체 → depth=3 시도 (LLM이 판단)

    전략:
    - Actor가 depth=3을 반환하면 그대로 유지 (특수 케이스)
    - Actor가 depth=1 또는 2를 반환하면 turn_count 기반 검증
    """
    # Condition A/B: Actor가 depth=3을 판단했으면 그대로 유지
    if actor_depth == 3:
        return 3

    # Condition C: turn_count 기반 기본 진행
    if current_turn_count == 1:
        return 1  # Turn 1: FACT
    elif current_turn_count == 2:
        return 2  # Turn 2: EMOTION
    else:
        return 2  # Turn 3+: EMOTION 유지


# ============ SamanthaPipeline ============


class SamanthaPipeline:
    """
    Samantha Direct 파이프라인

    [데이터 흐름]
    User → Rule-based Router → Always RAG → ExpandedActor → Response

    Rule-based priority/pacing/keyword 추출로 최소 레이턴시 달성.

    [의존성 주입]
    테스트 시 mock 객체 주입 가능
    """

    def __init__(
        self,
        store: Optional[SessionStore] = None,
        expanded_actor: Optional["ActorEngine"] = None,
        memory: Optional[MemoryEngine] = None,
    ):
        from app.engine.actor import get_actor_engine

        self.expanded_actor = expanded_actor or get_actor_engine()
        self.memory = memory or get_memory_engine()
        self.store = store or MemorySessionStore()
        self._conversation_pipeline = ConversationPipeline(self.store, self.memory)

    async def run(self, user_id: int, user_input: str, db: AsyncSession) -> str:
        """
        Direct 파이프라인 실행

        Raises:
            SamandaException 하위 클래스: 도메인 예외
            Exception: 예상치 못한 오류 (500)
        """
        return await self._run_direct(user_id, user_input, db)

    async def _run_direct(self, user_id: int, user_input: str, db: AsyncSession) -> str:
        """Direct 파이프라인: Always Retrieve → Actor"""
        from app.engine.actor import ActorContext

        try:
            # 1. 세션 초기화
            session = await self._conversation_pipeline.init_session(db, user_id)
            is_first_turn = len(session.conversation_history) == 0

            # 2. Always Retrieve — RAG 검색 (병렬 실행)
            retrieved_memories: List[str] = []
            try:
                profile_keywords = extract_profile_keywords_simple(user_input)
                recent_history = [turn.content for turn in session.conversation_history[-3:]]

                # Profile(동기) + Legacy(비동기) 병렬 실행
                async def _profile_search() -> List[str]:
                    if profile_keywords:
                        return search_profile_by_keywords(
                            user_profile=session.user_profile,
                            keywords=profile_keywords,
                            max_results=5,
                        )
                    return []

                async def _legacy_search() -> List[Any]:
                    if self._conversation_pipeline.memory_engine:
                        return await self._conversation_pipeline._search_legacy(
                            db, user_id, user_input, conversation_history=recent_history
                        )
                    return []

                profile_results, legacy_results = await asyncio.gather(
                    _profile_search(), _legacy_search(), return_exceptions=True,
                )

                if isinstance(profile_results, list):
                    retrieved_memories.extend(profile_results)
                else:
                    logger.error(f"Profile search failed (direct): {profile_results}")

                if isinstance(legacy_results, list):
                    legacy_summaries = [r.summary for r in legacy_results]
                    retrieved_memories.extend(legacy_summaries)
                else:
                    logger.error(f"Legacy search failed (direct): {legacy_results}")
            except Exception as e:
                logger.error(f"RAG retrieval failed (direct): user_id={user_id}, error={e}")

            # 4. 히스토리에 유저 발화 추가
            session.add_turn("user", user_input)

            # 5. Actor 컨텍스트 조립
            actor_context = self._build_actor_context(
                session, user_input, retrieved_memories,
            )

            # 6. Actor 실행
            actor_response = await self.expanded_actor.generate(actor_context)

            # 6a. Actor 분석 결과 로깅 (analysis-first 구조)
            if actor_response.priority_refined:
                logger.info(
                    "Actor analysis: user_id=%s, emotion=%s, priority=%s, instruction=%s",
                    user_id,
                    actor_response.user_emotion_refined,
                    actor_response.priority_refined,
                    (actor_response.immediate_instruction or "")[:80],
                )
                if actor_response.priority_refined == "REDLINE":
                    logger.warning("REDLINE detected by Actor: user_id=%s", user_id)

            # 7. Conversation tracker 적용 (Actor 출력 기반, rule-based fallback)
            tracker = self._parse_actor_conversation_tracker(
                actor_response.conversation_tracker, session, user_input, is_first_turn,
            )
            self._conversation_pipeline._validate_conversation_tracker(session, tracker)
            session.update_conversation_context(tracker)

            # 8. 5축 delta 적용
            if actor_response.axis_updates:
                self._apply_actor_axis_updates(session, actor_response.axis_updates)

            # 9. 히스토리 + 세션 저장 (동일 session 객체에서 1회만 영속화)
            self._conversation_pipeline.add_assistant_response(session, actor_response.response_text)
            await self._conversation_pipeline.update_session(user_id, session)

            # 10. Per-turn Profile/Legacy 추출 (fire-and-forget, 현재 턴만)
            task = asyncio.create_task(
                self._conversation_pipeline._per_turn_extract(
                    user_id, session, user_input, actor_response.response_text,
                ),
                name=f"bg_extraction_direct_user_{user_id}",
            )
            self._conversation_pipeline._background_tasks.add(task)
            task.add_done_callback(self._conversation_pipeline._on_legacy_task_done)

            return actor_response.response_text

        except RateLimitException:
            logger.warning(f"Pipeline (direct) rate limited: user_id={user_id}")
            return "지금 대화가 좀 많아서 잠깐 쉬어야 해요. 조금만 기다려 주세요!"
        except SamandaException as e:
            logger.error(f"Pipeline (direct) domain error: user_id={user_id}, code={e.code}, error={e}")
            return "아... 제가 지금 좀 멍하네요. 다시 한 번 말씀해 주시겠어요?"
        except Exception as e:
            logger.error(f"Pipeline (direct) unexpected error: user_id={user_id}, error={e}", exc_info=True)
            raise

    async def run_stream(
        self, user_id: int, user_input: str, db: AsyncSession
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 파이프라인 실행 - run_stream_with_voice에 위임"""
        async for event in self.run_stream_with_voice(user_id, user_input, db):
            yield event

    async def run_stream_with_voice(
        self,
        user_id: int,
        user_input: str,
        db: AsyncSession,
        prefetched_session: Optional["SessionData"] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Direct 스트리밍 파이프라인 실행

        Args:
            prefetched_session: STT 대기 중 사전 로드된 세션 (None이면 내부에서 init_session 호출)
        """
        async for event in self._run_stream_direct(
            user_id, user_input, db, prefetched_session,
        ):
            yield event

    async def _run_stream_direct(
        self,
        user_id: int,
        user_input: str,
        db: AsyncSession,
        prefetched_session: Optional["SessionData"] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Direct 스트리밍 파이프라인: Always Retrieve → ExpandedActor stream"""
        from app.engine.actor import ActorContext
        from app.engine.stream_processor import SentenceSegmenter, StreamingJsonParser

        if prefetched_session is not None:
            session = prefetched_session
            logger.debug("[Pipeline] Using prefetched session: user_id=%s", user_id)
        else:
            session = await self._conversation_pipeline.init_session(db, user_id)
        is_first_turn = len(session.conversation_history) == 0

        # Always Retrieve (병렬 실행)
        retrieved_memories: List[str] = []
        try:
            profile_keywords = extract_profile_keywords_simple(user_input)
            recent_history = [turn.content for turn in session.conversation_history[-3:]]

            async def _profile_search() -> List[str]:
                if profile_keywords:
                    return search_profile_by_keywords(
                        user_profile=session.user_profile,
                        keywords=profile_keywords,
                        max_results=5,
                    )
                return []

            async def _legacy_search() -> List[Any]:
                if self._conversation_pipeline.memory_engine:
                    return await self._conversation_pipeline._search_legacy(
                        db, user_id, user_input, conversation_history=recent_history
                    )
                return []

            profile_results, legacy_results = await asyncio.gather(
                _profile_search(), _legacy_search(), return_exceptions=True,
            )

            if isinstance(profile_results, list):
                retrieved_memories.extend(profile_results)
            else:
                logger.error(f"Profile search failed (direct-stream): {profile_results}")

            legacy_for_frontend: List[Dict[str, Any]] = []
            if isinstance(legacy_results, list):
                legacy_summaries = [r.summary for r in legacy_results]
                retrieved_memories.extend(legacy_summaries)
                legacy_for_frontend = [
                    {"id": r.id, "summary": r.summary, "category": r.category.value, "importance": r.importance}
                    for r in legacy_results
                ]
            else:
                logger.error(f"Legacy search failed (direct-stream): {legacy_results}")
        except Exception as e:
            logger.error(f"RAG retrieval failed (direct-stream): user_id={user_id}, error={e}")

        # RAG 결과 프론트 전송 (Actor 스트리밍 시작 전)
        yield {"type": "rag_results", "seq": 0, "data": {
            "legacy_results": legacy_for_frontend,
            "profile_results": profile_results if isinstance(profile_results, list) else [],
        }}

        # 히스토리 추가
        session.add_turn("user", user_input)

        # Actor 컨텍스트
        actor_context = self._build_actor_context(
            session, user_input, retrieved_memories,
        )

        # 스트리밍
        parser = StreamingJsonParser()
        actor_tracker = None  # 스트리밍 중 수집
        # TTFA 개선: 첫 세그먼트 생성 임계치를 낮춰 TTS를 더 빨리 시작한다.
        segmenter = SentenceSegmenter(min_chars=18, max_chars=180, soft_timeout_ms=250)
        seq = 1  # rag_results가 seq=0 사용
        control_signals_yielded = False
        axis_updates_applied = False  # axis_updates 이중 적용 방지
        current_deltas: dict[str, float] = {}  # 이번 턴의 delta (expression 도출용)

        try:
            async for chunk in self.expanded_actor.generate_stream(actor_context):
                result = parser.feed(chunk)
                if result.axis_updates and not axis_updates_applied:
                    current_deltas = result.axis_updates.extract_deltas()
                    self._apply_actor_axis_updates(session, result.axis_updates)
                    axis_updates_applied = True
                    # 5축 delta → expression/emotion 도출 (axis_updates 수신 즉시)
                    if not control_signals_yielded:
                        derived = session.persona_state.derive_expression(deltas=current_deltas)
                        yield {"type": "tts_config", "seq": seq, "data": {
                            "emotion": derived.emotion,
                        }}
                        seq += 1
                        yield {"type": "live2d", "seq": seq, "data": {
                            "expression": derived.expression,
                        }}
                        seq += 1
                        control_signals_yielded = True
                if result.conversation_tracker:
                    actor_tracker = result.conversation_tracker
                for text in result.text_chunks:
                    yield {"type": "text", "seq": seq, "data": text}
                    seq += 1
                    for seg in segmenter.feed(text):
                        yield {"type": "tts", "seq": seq, "data": seg.text}
                        seq += 1
                if result.is_done:
                    break

            final = parser.finish()
            for text in final.text_chunks:
                yield {"type": "text", "seq": seq, "data": text}
                seq += 1
                for seg in segmenter.feed(text):
                    yield {"type": "tts", "seq": seq, "data": seg.text}
                    seq += 1
            if final.axis_updates and not axis_updates_applied:
                current_deltas = final.axis_updates.extract_deltas()
                self._apply_actor_axis_updates(session, final.axis_updates)
                axis_updates_applied = True
            if final.conversation_tracker:
                actor_tracker = final.conversation_tracker
            for seg in segmenter.flush():
                yield {"type": "tts", "seq": seq, "data": seg.text}
                seq += 1

            # Control signal 보장: axis_updates가 없었어도 현재 state 기반으로 도출
            if not control_signals_yielded:
                logger.warning("No axis_updates received, deriving from current persona_state")
                derived = session.persona_state.derive_expression(deltas=current_deltas or None)
                yield {"type": "tts_config", "seq": seq, "data": {
                    "emotion": derived.emotion,
                }}
                seq += 1
                yield {"type": "live2d", "seq": seq, "data": {
                    "expression": derived.expression,
                }}
                seq += 1

            # Conversation tracker 적용 (Actor 출력 기반, rule-based fallback)
            tracker = self._parse_actor_conversation_tracker(
                actor_tracker, session, user_input, is_first_turn,
            )
            self._conversation_pipeline._validate_conversation_tracker(session, tracker)
            session.update_conversation_context(tracker)

            full_text = parser.full_response_text
            if full_text:
                self._conversation_pipeline.add_assistant_response(session, full_text)
            await self._conversation_pipeline.update_session(user_id, session)

            # Per-turn Profile/Legacy 추출 (fire-and-forget, 현재 턴만)
            if full_text:
                task = asyncio.create_task(
                    self._conversation_pipeline._per_turn_extract(
                        user_id, session, user_input, full_text,
                    ),
                    name=f"bg_extraction_direct_stream_user_{user_id}",
                )
                self._conversation_pipeline._background_tasks.add(task)
                task.add_done_callback(self._conversation_pipeline._on_legacy_task_done)

            # 디버그 정보 전송 (done 직전)
            yield {"type": "debug_info", "seq": seq, "data": {
                "persona_state": {
                    f"axis_{k}": v for k, v in session.persona_state.to_dict().items()
                },
                "user_profile": session.user_profile,
                "conversation_context": {
                    "turn_count": session.conversation_context.turn_count,
                    "depth_level": session.conversation_context.depth_level,
                    "pacing": session.conversation_context.conversation_pacing.value,
                },
            }}
            seq += 1

            yield {"type": "done", "seq": seq}

        except asyncio.CancelledError:
            partial_text = parser.full_response_text
            if partial_text:
                self._conversation_pipeline.add_assistant_response(session, partial_text)
                await self._conversation_pipeline.update_session(user_id, session)
            raise
        except RateLimitException:
            logger.warning(f"Pipeline (stream) rate limited: user_id={user_id}")
            yield {"type": "text", "seq": seq, "data": "지금 대화가 좀 많아서 잠깐 쉬어야 해요. 조금만 기다려 주세요!"}
            yield {"type": "done", "seq": seq + 1}
        except SamandaException as e:
            logger.error(f"Pipeline (stream) domain error: user_id={user_id}, code={e.code}, error={e}")
            yield {"type": "text", "seq": seq, "data": "아... 제가 지금 좀 멍하네요. 다시 한 번 말씀해 주시겠어요?"}
            yield {"type": "done", "seq": seq + 1}

    def _build_actor_context(
        self,
        session: SessionData,
        user_input: str,
        retrieved_memories: List[str],
    ) -> Any:
        """Actor 컨텍스트 조립 (priority 판단은 Actor에 위임)"""
        from app.engine.actor import ActorContext

        conv_ctx = session.get_conversation_context()
        rapport_tier = session.user_profile.get("rapport_tier", "STRANGER")
        current_time_str = now_kst().strftime("%Y-%m-%d %H:%M")

        history = session.get_history_as_messages()
        if history and history[-1].get("role") == "user" and history[-1].get("content") == user_input:
            history = history[:-1]

        preset_info = PERSONA_PRESETS.get(session.persona_type, {})
        persona_name = preset_info.get("name", session.persona_type)
        persona_desc = preset_info.get("description", "")
        persona_description = f"{persona_name}: {persona_desc}" if persona_desc else persona_name
        preference = session.user_profile.get("PREFERENCE", {})
        configured_assistant_name = preference.get("assistant_name", "시아")
        if isinstance(configured_assistant_name, list):
            configured_assistant_name = configured_assistant_name[-1] if configured_assistant_name else "시아"
        if not isinstance(configured_assistant_name, str) or not configured_assistant_name.strip():
            configured_assistant_name = "시아"

        return ActorContext(
            user_input_text=user_input,
            retrieved_memories=retrieved_memories,
            conversation_pacing=conv_ctx.conversation_pacing.value,
            depth_level=conv_ctx.depth_level,
            turn_count=conv_ctx.turn_count,
            consecutive_probe_count=conv_ctx.consecutive_probe_count,
            consecutive_absorb_count=conv_ctx.consecutive_absorb_count,
            user_emotion="neutral",
            force_topic=None,
            next_move="",
            persona_state=session.persona_state.to_dict(),
            user_title=session.user_title,
            rapport_tier=rapport_tier,
            user_profile=session.user_profile,
            persona_type=session.persona_type,
            persona_description=persona_description,
            conversation_history=history,
            current_time_str=current_time_str,
            assistant_name=configured_assistant_name,
        )

    def _parse_actor_conversation_tracker(
        self,
        actor_tracker: Optional[ConversationTracker],
        session: SessionData,
        user_input: str,
        is_first_turn: bool,
    ) -> "ConversationTracker":
        """
        Actor 출력 → ConversationTracker 변환

        P0: actor_tracker는 이제 타입 검증된 ConversationTracker 모델
        LLM에게 연속 카운트를 전달하여 pacing을 자율 결정하게 하고,
        파이프라인은 카운트 추적만 담당.
        """
        conv_ctx = session.get_conversation_context()

        if actor_tracker:
            # CRITICAL: turn_count는 파이프라인에서 직접 관리
            is_new_topic = actor_tracker.is_new_topic
            if is_new_topic or is_first_turn:
                actual_turn_count = 1
            else:
                actual_turn_count = conv_ctx.turn_count + 1

            # LLM pacing 값 검증
            llm_pacing = actor_tracker.conversation_pacing.value
            if llm_pacing not in ("PROBE", "ABSORB"):
                llm_pacing = "PROBE"

            # consecutive 카운트 업데이트 (새 토픽/첫 턴이면 리셋)
            if is_new_topic or is_first_turn:
                new_probe_count = 1 if llm_pacing == "PROBE" else 0
                new_absorb_count = 1 if llm_pacing == "ABSORB" else 0
            else:
                new_probe_count = (conv_ctx.consecutive_probe_count + 1) if llm_pacing == "PROBE" else 0
                new_absorb_count = (conv_ctx.consecutive_absorb_count + 1) if llm_pacing == "ABSORB" else 0

            # depth_level: Condition C만 강제, Condition A/B는 LLM 판단 유지
            actor_depth = actor_tracker.depth_level
            depth_level = compute_depth_level_simple(actor_depth, actual_turn_count)

            logger.info(
                f"[TRACKER DEBUG] "
                f"is_first_turn={is_first_turn}, "
                f"is_new_topic={is_new_topic}, "
                f"llm_pacing={llm_pacing}, "
                f"consecutive_probe={new_probe_count}, "
                f"consecutive_absorb={new_absorb_count}, "
                f"actual_turn={actual_turn_count}, "
                f"actor_depth={actor_depth}, "
                f"computed_depth={depth_level}"
            )

            return ConversationTracker(
                topic=actor_tracker.topic or user_input[:30],
                depth_level=depth_level,
                turn_count=actual_turn_count,
                conversation_pacing=ConversationPacing(llm_pacing),
                consecutive_probe_count=new_probe_count,
                consecutive_absorb_count=new_absorb_count,
                is_new_topic=bool(is_new_topic),
                next_move=actor_tracker.next_move,
            )

        # Fallback: Actor가 tracker를 반환하지 않은 경우
        logger.warning("Actor did not return conversation_tracker, using fallback")
        actual_turn = 1 if is_first_turn else conv_ctx.turn_count + 1
        return ConversationTracker(
            topic=user_input[:30],
            depth_level=min(3, conv_ctx.depth_level + 1),
            turn_count=actual_turn,
            conversation_pacing=ConversationPacing.PROBE,
            consecutive_probe_count=1,
            consecutive_absorb_count=0,
            is_new_topic=False,
            next_move="",
        )

    def _apply_actor_axis_updates(self, session: SessionData, axis_updates: Optional[AxisUpdates]) -> None:
        """Actor가 반환한 axis_updates를 세션에 적용 (P1: 타입 검증됨)

        Args:
            axis_updates: AxisUpdates 모델 (검증됨) 또는 None
        """
        if not axis_updates:
            return

        # AxisUpdates.extract_deltas()로 순수 delta만 추출
        deltas = axis_updates.extract_deltas()
        if deltas:
            session.persona_state.apply_deltas(deltas)
            logger.info(f"Actor axis deltas applied: {deltas}")

# ============ Factory ============


def create_pipeline(use_redis: bool = False) -> ConversationPipeline:
    """
    파이프라인 팩토리

    Usage:
        # 개발
        pipeline = create_pipeline(use_redis=False)

        # 프로덕션
        pipeline = create_pipeline(use_redis=True)
    """
    if use_redis:
        from app.core.config import settings

        store = RedisSessionStore(settings.REDIS_URL, ttl=settings.SESSION_TIMEOUT)
    else:
        store = MemorySessionStore()

    return ConversationPipeline(store)


# 기본 인스턴스 (개발용 - Memory)
pipeline = create_pipeline(use_redis=False)
