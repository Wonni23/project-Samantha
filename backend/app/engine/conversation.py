# backend/app/engine/conversation.py
"""
대화 파이프라인 — 세션 관리 + 분석 처리 + Legacy/Profile 영속화

[역할]
1. 세션 관리 (초기화, 조회, 업데이트, 종료)
2. Actor 결과 처리 (conversation_tracker 검증)
3. RAG 검색 (Legacy 벡터 검색)
4. Per-turn Profile/Legacy 추출 (fire-and-forget)
5. 대화 txt 내보내기 + LLM 요약
"""
from __future__ import annotations

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import update, func

from app.core.config import now_kst
from app.engine.memory import MemoryEngine, MAX_IMPORTANCE
from app.engine.session_store import SessionStore
from app.models.content import LifeLegacy
from app.models.enums import LegacyCategory, PersonaType
from app.models.user_context import UserContext
from app.schemas.conversation_schema import (
    ConversationPacing,
    ConversationTracker,
    ExtractedLegacy,
    ExtractedProfile,
)
from app.schemas.session_schema import PersonaState, SessionData

logger = logging.getLogger(__name__)

def _get_or_create_preference(session: SessionData) -> Dict[str, Any]:
    """user_profile 내 PREFERENCE 섹션을 보장해 반환."""
    if "PREFERENCE" not in session.user_profile:
        session.user_profile["PREFERENCE"] = {}
    return session.user_profile["PREFERENCE"]


class ConversationPipeline:
    """
    대화 파이프라인

    [역할]
    1. 세션 관리 (초기화, 조회, 업데이트, 종료)
    2. Actor 결과 처리 (5축 delta, 프로필, 레거시)
    3. Actor 컨텍스트 조립
    4. RAG 조건부 호출

    [사용법]
    # 개발환경
    from app.engine.session_store import MemorySessionStore
    pipeline = ConversationPipeline(MemorySessionStore())

    # 프로덕션
    from app.engine.session_store import RedisSessionStore
    pipeline = ConversationPipeline(RedisSessionStore(settings.REDIS_URL))
    """

    def __init__(
        self,
        store: SessionStore,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self.store = store
        self.memory_engine = memory_engine
        self._background_tasks: set[asyncio.Task] = set()

    # ============ 세션 관리 ============

    async def init_session(self, db: AsyncSession, user_id: int) -> SessionData:
        """
        세션 초기화 - DB에서 데이터 로드 후 캐시

        [호출 시점] 세션 시작 (첫 연결, 첫 메시지)

        Raises:
            DB/네트워크 예외는 상위로 전파 (빈 세션 반환 방지)
        """
        # 1. 캐시 확인 (캐시 실패는 무시하고 DB에서 로드)
        try:
            cached = await self.store.get(user_id)
            if cached:
                logger.info(f"Session cache hit: user_id={user_id}")
                cached.last_active_at = now_kst()
                await self.store.set(user_id, cached)
                return cached
        except Exception as e:
            logger.warning(f"Session cache lookup failed, loading from DB: user_id={user_id}, error={e}")

        # 2. DB에서 UserContext 로드 (실패 시 예외 전파)
        user_context = await self._load_user_context(db, user_id)
        if not user_context:
            logger.warning(
                f"UserContext not found, creating default: user_id={user_id}"
            )
            user_context = await self._create_default_context(db, user_id)

        # 3. SessionData 생성
        session_data = SessionData(
            user_id=user_id,
            persona_type=user_context.current_persona.value,
            user_title=user_context.user_title,
            persona_state=PersonaState.from_user_context(user_context),
            user_profile=user_context.user_profile or {},
            last_summary=user_context.last_summary or {},
        )

        # 4. 캐시 저장 (캐시 실패는 무시 - 다음 요청에서 재시도)
        try:
            await self.store.set(user_id, session_data)
        except Exception as e:
            logger.warning(f"Session cache save failed: user_id={user_id}, error={e}")

        logger.info(f"Session initialized: user_id={user_id}")
        return session_data

    async def get_session(self, user_id: int) -> Optional[SessionData]:
        """캐시에서 세션 조회"""
        return await self.store.get(user_id)

    async def update_session(self, user_id: int, session: SessionData) -> None:
        """세션 업데이트"""
        session.last_active_at = now_kst()
        await self.store.set(user_id, session)

    async def save_to_db(self, db: AsyncSession, user_id: int) -> None:
        """
        세션 데이터를 DB에 영구 저장

        Raises:
            Exception: DB 저장 실패 시 예외 전파 (데이터 손실 방지)
        """
        session = await self.store.get(user_id)
        if not session:
            logger.warning(f"No session to save: user_id={user_id}")
            return

        user_context = await self._load_user_context(db, user_id)
        if not user_context:
            logger.warning(f"UserContext not found, creating default: user_id={user_id}")
            user_context = await self._create_default_context(db, user_id)

        # 5축 상태 업데이트
        user_context.axis_playful = session.persona_state.playful
        user_context.axis_feisty = session.persona_state.feisty
        user_context.axis_dependent = session.persona_state.dependent
        user_context.axis_caregive = session.persona_state.caregive
        user_context.axis_reflective = session.persona_state.reflective

        # Profile/user_title: 매 턴 _save_profile_background에서 영속화됨

        # 세션 요약 업데이트
        user_context.last_summary = session.last_summary

        db.add(user_context)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        logger.info(f"Session saved to DB: user_id={user_id}")

    async def end_session(
        self,
        db: AsyncSession,
        user_id: int,
        save: bool = True,
        export_txt: bool = True,
        summarize: bool = True,
    ) -> None:
        """
        세션 종료

        Args:
            db: DB 세션
            user_id: 유저 ID
            save: DB에 저장 여부
            export_txt: 대화 txt 내보내기 여부 (raw 대화만)
            summarize: LLM 요약 생성 여부 (DB 저장용)

        Raises:
            Exception: DB 저장 실패 시 예외 전파 (데이터 손실 방지)
        """
        # 1. Profile/Legacy 추출 — per-turn 추출로 이전, 세션 종료 시 별도 추출 불필요

        # 2. LLM 요약 생성 (비필수 - 실패해도 계속)
        if summarize:
            try:
                summary = await self._summarize_conversation(user_id)
                if summary:
                    session = await self.store.get(user_id)
                    if session:
                        session.last_summary = summary
                        await self.update_session(user_id, session)
                        logger.info(f"Conversation summary generated: user_id={user_id}")
            except Exception as e:
                logger.warning(f"Summary generation failed (non-critical): user_id={user_id}, error={e}")

        # 4. 대화 txt 내보내기 (비필수 - 실패해도 계속)
        if export_txt:
            try:
                exported_path = await self.export_conversation_to_txt(user_id)
                if exported_path:
                    logger.info(f"Conversation exported: {exported_path}")
            except Exception as e:
                logger.warning(f"Export failed (non-critical): user_id={user_id}, error={e}")

        # 5. DB 저장 (필수 - 실패 시 예외 전파)
        if save:
            await self.save_to_db(db, user_id)

        # 6. 세션 삭제
        await self.store.delete(user_id)
        logger.info(f"Session ended: user_id={user_id}")

    # ============ Actor 결과 처리 ============

    def _validate_conversation_tracker(
        self, session: SessionData, tracker: "ConversationTracker"
    ) -> None:
        """
        conversation_tracker 검증 및 보정 (Task 6 규칙 강제)

        [규칙]
        1a. 3연속 PROBE 방지 → ABSORB로 강제
        1b. 2연속 ABSORB 방지 → PROBE로 강제
        2. 새 주제(is_new_topic) 시 depth=1, turn=1 강제
        3. 같은 주제 시 turn_count 최소 증가 검증
        """
        prev_context = session.conversation_context

        # 규칙 1a: 3연속 PROBE 방지 (가드레일 이중 안전망)
        if (tracker.conversation_pacing == ConversationPacing.PROBE and
            prev_context.consecutive_probe_count >= 2):
            logger.info(
                f"Pacing correction: 3 consecutive PROBEs detected "
                f"(prev_consecutive={prev_context.consecutive_probe_count}), forcing ABSORB"
            )
            tracker.conversation_pacing = ConversationPacing.ABSORB
            tracker.consecutive_probe_count = 0

        # 규칙 1b: 2연속 ABSORB 방지
        if (tracker.conversation_pacing == ConversationPacing.ABSORB and
            prev_context.conversation_pacing == ConversationPacing.ABSORB):
            logger.info(
                "Pacing correction: 2 consecutive ABSORBs detected, forcing PROBE"
            )
            tracker.conversation_pacing = ConversationPacing.PROBE
            tracker.consecutive_probe_count = 1

        # 규칙 2: 새 주제 시 depth=1, turn=1 강제
        if tracker.is_new_topic:
            if tracker.depth_level != 1:
                logger.info(
                    f"Depth correction: new topic but depth={tracker.depth_level}, forcing 1"
                )
                tracker.depth_level = 1
            if tracker.turn_count != 1:
                logger.info(
                    f"Turn correction: new topic but turn={tracker.turn_count}, forcing 1"
                )
                tracker.turn_count = 1

        # 규칙 3: 같은 주제 시 turn_count 최소 증가 검증
        if not tracker.is_new_topic:
            expected_turn = prev_context.turn_count + 1
            if tracker.turn_count < expected_turn:
                logger.info(
                    f"Turn correction: same topic but turn={tracker.turn_count} < expected {expected_turn}"
                )
                tracker.turn_count = expected_turn

    def _on_legacy_task_done(self, task: asyncio.Task) -> None:
        """백그라운드 Legacy 저장 태스크 완료 콜백"""
        self._background_tasks.discard(task)
        if task.cancelled():
            logger.warning(f"Legacy save task cancelled: {task.get_name()}")
        elif exc := task.exception():
            logger.error(
                f"Legacy save task failed unexpectedly: {task.get_name()}, error={exc}"
            )

    async def _save_profile_background(
        self,
        user_id: int,
        user_profile: Dict[str, Any],
        user_title: str,
        persona_state: Optional["PersonaState"] = None,
    ) -> None:
        """
        백그라운드 Profile + 5축 DB 저장 (독립 DB 세션 사용)

        세션 종료 대기 없이 매 턴 Profile/5축을 DB에 영속화.
        서버 크래시 시 데이터 유실 방지.
        """
        from app.core.db import async_session_factory

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with async_session_factory() as db:
                    user_context = await self._load_user_context(db, user_id)
                    if not user_context:
                        logger.warning(f"Profile save skipped - no UserContext: user_id={user_id}")
                        return

                    user_context.user_profile = user_profile
                    user_context.user_title = user_title

                    if persona_state is not None:
                        user_context.axis_playful = persona_state.playful
                        user_context.axis_feisty = persona_state.feisty
                        user_context.axis_dependent = persona_state.dependent
                        user_context.axis_caregive = persona_state.caregive
                        user_context.axis_reflective = persona_state.reflective

                    db.add(user_context)
                    await db.commit()
                    logger.info(f"Profile+axis saved (background): user_id={user_id}, attempt={attempt + 1}")
                    return
            except Exception as e:
                logger.error(
                    f"Profile save failed (background): user_id={user_id}, "
                    f"attempt={attempt + 1}/{max_retries}, error={e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    logger.error(
                        f"Profile save abandoned after {max_retries} attempts: user_id={user_id}"
                    )

    async def _save_legacy_background(
        self, user_id: int, legacy_info: Dict[str, Any]
    ) -> None:
        """
        백그라운드 Legacy 저장 (독립 DB 세션 사용)

        Args:
            user_id: 사용자 ID
            legacy_info: 저장할 레거시 정보
        """
        from app.core.db import async_session_factory

        # 재시도 로직
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 새 DB 세션 생성 (중요: 기존 세션 재사용 금지)
                async with async_session_factory() as db:
                    await self._save_legacy(db, user_id, legacy_info)
                    logger.info(
                        f"Legacy saved successfully (background): user_id={user_id}, "
                        f"attempt={attempt + 1}"
                    )
                    return
            except Exception as e:
                logger.error(
                    f"Legacy save failed (background): user_id={user_id}, "
                    f"attempt={attempt + 1}/{max_retries}, error={e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # 지수 백오프
                else:
                    logger.error(
                        f"Legacy save abandoned after {max_retries} attempts: user_id={user_id}"
                    )

    async def _search_legacy(
        self, db: AsyncSession, user_id: int, query: str,
        conversation_history: Optional[List[str]] = None,
    ) -> List[LifeLegacy]:
        """Legacy 벡터 검색 (대화 맥락 부스트)

        반환: LifeLegacy 객체 리스트 (호출측에서 summary 추출 및 프론트용 데이터 구성)

        Args:
            conversation_history: 최근 대화 이력 (List[str]) — Context Boost에 사용
        """
        memory_engine = self.memory_engine
        if memory_engine is None:
            logger.warning(
                "MemoryEngine not initialized, skipping legacy search: user_id=%s",
                user_id,
            )
            return []

        results = await memory_engine.search_memory_hybrid(
            db=db,
            query_text=query,
            user_id=user_id,
            categories=None,
            final_limit=3,
            conversation_history=conversation_history,
        )

        logger.debug(
            f"Legacy search: query='{query}', "
            f"results={len(results)}, context_boost={'enabled' if conversation_history else 'disabled'}"
        )
        return results

    def add_assistant_response(
        self, session: SessionData, response: str
    ) -> None:
        """
        Actor 응답을 로컬 세션의 히스토리에 추가.
        store 재로드 없이 동일 session 객체에 직접 추가한다.
        """
        session.add_turn("assistant", response)

    # ============ Per-Turn Extraction ============

    async def _apply_extraction_result(
        self,
        user_id: int,
        session: SessionData,
        profiles: List[Dict[str, Any]],
        legacies: List[Dict[str, Any]],
    ) -> None:
        """추출 결과를 세션 + DB에 적용 (P3: Pydantic 검증).

        Args:
            profiles: [{"category": "FAMILY", "key": "son_name", "value": "철수"}, ...]
            legacies: [{"legacy_type": "EPISODE", "content": "...", "importance": 3}, ...]
        """
        validated_profiles: List[ExtractedProfile] = []
        for raw in profiles:
            try:
                p = ExtractedProfile(**raw)
                validated_profiles.append(p)
            except (TypeError, ValueError) as e:
                logger.warning(f"Extraction profile validation failed: {e}, raw={raw}")

        for p in validated_profiles:
            if p.key == "assistant_name":
                pref = _get_or_create_preference(session)
                pref["assistant_name"] = p.value
                logger.info(
                    "Extraction assistant_name applied: "
                    f"user_id={user_id}, value={p.value}"
                )
                continue

            if p.key == "preferred_title":
                # preferred_title은 교체 (누적 X)
                pref = _get_or_create_preference(session)
                pref["preferred_title"] = p.value
                session.user_title = p.value
                logger.info(
                    "Extraction preferred_title applied: "
                    f"user_id={user_id}, value={p.value}"
                )
                continue

            session.update_profile(p.category, {p.key: p.value})
            logger.info(f"Extraction profile applied: user_id={user_id}, {p.category}.{p.key}")

        validated_legacies: List[ExtractedLegacy] = []
        for raw in legacies:
            try:
                leg = ExtractedLegacy(**raw)
                validated_legacies.append(leg)
            except (TypeError, ValueError) as e:
                logger.warning(f"Extraction legacy validation failed: {e}, raw={raw}")

        for leg in validated_legacies:
            legacy_info = {
                "category": leg.legacy_type.lower(),
                "content": leg.content,
                "importance": leg.importance,
            }
            task = asyncio.create_task(
                self._save_legacy_background(user_id, legacy_info),
                name=f"extraction_legacy_user_{user_id}",
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._on_legacy_task_done)

        if validated_profiles:
            await self.store.set(user_id, session)

    async def _per_turn_extract(
        self,
        user_id: int,
        session: SessionData,
        user_input: str,
        actor_response_text: str,
    ) -> None:
        """매 턴 후 Profile/Legacy 경량 추출 (background, fire-and-forget).

        현재 턴만(user_input + actor_response) 분석하여 즉시 세션에 반영.
        critical path 밖에서 실행 → 레이턴시 영향 0.

        TODO(concurrency): 현재 MemorySessionStore(dict 참조 공유)에서는 안전하지만,
        RedisSessionStore 전환 시 직렬화 기반이므로 레이스 컨디션 발생 가능.
        → store에서 최신 세션 reload 후 merge, 또는 user_id 단위 lock 필요.
        """
        from app.engine.prompts import EXTRACTION_SYSTEM_PROMPT
        from app.integrations.llm.gemini_provider import GeminiProvider
        from app.integrations.llm.base import GenerationConfig

        try:
            if not user_input or not actor_response_text:
                return

            profile_summary = json.dumps(session.user_profile, ensure_ascii=False) if session.user_profile else "{}"

            prompt = f"""{EXTRACTION_SYSTEM_PROMPT}

[사용자 발화]
{user_input}

[현재 유저 프로필 (이미 저장된 정보 — 중복 추출 금지)]
{profile_summary}

위 사용자 발화에서 새로운 정보를 추출해주세요.
"""

            llm = GeminiProvider()
            config = GenerationConfig(temperature=0.3)
            result_dict = await llm.generate_structured(prompt, config)

            # LLM dict 직접 파싱 — fallback: category→PREFERENCE, legacy_type→EPISODE
            profiles = [
                p for p in result_dict.get("profiles", [])
                if isinstance(p, dict) and p.get("key") and p.get("value")
            ]
            legacies = [
                {
                    "legacy_type": l_item.get("legacy_type", "EPISODE"),
                    "content": l_item["content"],
                    "importance": min(5, max(1, int(l_item.get("importance", 1)))),
                }
                for l_item in result_dict.get("legacies", [])
                if isinstance(l_item, dict) and l_item.get("content")
            ]

            if profiles or legacies:
                await self._apply_extraction_result(user_id, session, profiles, legacies)
                logger.info(
                    f"Per-turn extraction: user_id={user_id}, "
                    f"profiles={len(profiles)}, legacies={len(legacies)}"
                )

        except Exception as e:
            logger.debug(f"Per-turn extraction failed (non-critical): user_id={user_id}, error={e}")

        # Profile + 5축을 매 턴 DB에 영속화 (추출 유무/예외 발생과 무관하게 항상 저장)
        task = asyncio.create_task(
            self._save_profile_background(
                user_id, session.user_profile, session.user_title,
                persona_state=session.persona_state,
            ),
            name=f"bg_profile_save_user_{user_id}",
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._on_legacy_task_done)

    # ============ Private Methods ============

    async def _load_user_context(
        self, db: AsyncSession, user_id: int
    ) -> Optional[UserContext]:
        """DB에서 UserContext 로드"""
        statement = select(UserContext).where(UserContext.user_id == user_id)
        result = await db.exec(statement)
        return result.first()

    async def _create_default_context(
        self, db: AsyncSession, user_id: int
    ) -> UserContext:
        """신규 유저용 기본 UserContext 생성"""
        user_context = UserContext(
            user_id=user_id,
            current_persona=PersonaType.SIA_FEMALE,
            user_title="선생님",
            user_profile={},
            last_summary={},
        )
        db.add(user_context)
        await db.commit()
        await db.refresh(user_context)
        return user_context

    def _merge_summaries(self, old: str, new: str) -> str:
        """
        두 요약을 병합 (중복 제거, 정보 보완)

        Phase 1: 단순 로직 - 더 긴 내용 유지
        향후: LLM 기반 스마트 병합 가능

        Args:
            old: 기존 요약
            new: 새 요약

        Returns:
            병합된 요약
        """
        return new if len(new) > len(old) else old

    async def _save_legacy(
        self, db: AsyncSession, user_id: int, extracted_info: Dict[str, Any]
    ) -> None:
        """
        레거시(자서전) 정보 저장 (중복 시 importance 증가)

        Args:
            db: DB 세션
            user_id: 유저 ID
            extracted_info: Extraction이 추출한 정보
                - category: 카테고리 (health, relationship, career, taste, values, general)
                - content: 저장할 내용 (3인칭으로 정제된 요약)
                - tags: 태그 리스트 (선택)
        """
        try:
            # 1. extracted_info에서 데이터 추출
            category_str = extracted_info.get("category", "general")
            content = extracted_info.get("content", "")

            if not content:
                logger.warning(f"Empty content, skipping legacy save: user_id={user_id}")
                return

            # 2. 카테고리 변환 (문자열 → Enum)
            try:
                category = LegacyCategory(category_str.lower())
            except ValueError:
                category = LegacyCategory.EPISODE
                logger.warning(f"Unknown category '{category_str}', using EPISODE as fallback")

            # 3. 임베딩 생성
            if not self.memory_engine:
                logger.error("MemoryEngine not initialized, cannot save legacy")
                return

            embedding = await self.memory_engine.get_embedding(content)

            # 4. 중복 체크: 유사 메모리 검색 (MemoryEngine에 위임)
            similar = await self.memory_engine.find_duplicate_legacy(
                db,
                user_id=user_id,
                embedding=embedding,
                category=category,
            )

            if similar:
                # 5a. 기존 메모리 병합: 원자적 UPDATE로 importance 증가
                merged_summary = self._merge_summaries(similar.summary, content)

                # meta_info None 방어
                if similar.meta_info is None:
                    similar.meta_info = {}
                similar.meta_info["last_mentioned_at"] = now_kst().isoformat()

                stmt = (
                    update(LifeLegacy)
                    .where(LifeLegacy.id == similar.id)
                    .values(
                        importance=func.least(LifeLegacy.importance + 1, MAX_IMPORTANCE),
                        summary=merged_summary,
                        meta_info=similar.meta_info,
                    )
                )
                await db.execute(stmt)
                await db.commit()

                logger.info(
                    f"Legacy merged: user_id={user_id}, category={category.value}, "
                    f"legacy_id={similar.id}, new_importance<={MAX_IMPORTANCE}"
                )
            else:
                # 5b. 신규 메모리 저장
                meta_info = {
                    "extracted_at": now_kst().isoformat(),
                }
                if "tags" in extracted_info:
                    meta_info["tags"] = extracted_info["tags"]

                legacy = LifeLegacy(
                    user_id=user_id,
                    category=category,
                    summary=content,
                    embedding=embedding,
                    meta_info=meta_info,
                    importance=extracted_info.get("importance") or 1,  # Extraction 판단값, None이면 1
                    is_public=False,
                )

                db.add(legacy)
                await db.commit()

                logger.info(
                    f"Legacy saved: user_id={user_id}, category={category.value}, "
                    f"content_length={len(content)}"
                )

        except Exception as e:
            logger.error(f"Failed to save legacy: user_id={user_id}, error={e}")
            await db.rollback()
            raise  # 백그라운드 재시도를 위해 예외 전파

    async def export_conversation_to_txt(
        self,
        user_id: int,
        output_dir: Optional[str] = None,
    ) -> Optional[str]:
        """
        대화 히스토리를 txt 파일로 내보내기

        Args:
            user_id: 유저 ID
            output_dir: 저장 경로 (기본: backend/data/conversations/)

        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        try:
            # 1. 세션 조회
            session = await self.store.get(user_id)
            if not session:
                logger.warning(f"No session to export: user_id={user_id}")
                return None

            if not session.conversation_history:
                logger.warning(f"Empty conversation history: user_id={user_id}")
                return None

            # 2. 출력 디렉토리 설정
            if output_dir is None:
                # 기본 경로: backend/data/conversations/
                base_dir = Path(__file__).parent.parent.parent / "data" / "conversations"
            else:
                base_dir = Path(output_dir)

            # 유저별 폴더 생성
            user_dir = base_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)

            # 3. 파일명 생성 (날짜_시간 형식)
            timestamp = now_kst().strftime("%Y%m%d_%H%M%S")
            session_start = session.session_started_at.strftime("%Y%m%d_%H%M")
            filename = f"conversation_{session_start}_{timestamp}.txt"
            file_path = user_dir / filename

            # 4. 대화 내용 포맷팅
            lines = []
            lines.append("=" * 60)
            lines.append(f"사용자 ID: {user_id}")
            lines.append(f"페르소나: {session.persona_type}")
            lines.append(f"세션 시작: {session.session_started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"내보내기 시간: {now_kst().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"총 대화 턴: {len(session.conversation_history)}")
            lines.append("=" * 60)
            lines.append("")

            for turn in session.conversation_history:
                timestamp_str = turn.timestamp.strftime("%H:%M:%S")
                speaker = "사용자" if turn.role == "user" else "사만다"
                lines.append(f"[{timestamp_str}] {speaker}:")
                lines.append(f"  {turn.content}")
                lines.append("")

            lines.append("=" * 60)
            lines.append("대화 종료")
            lines.append("=" * 60)

            # 5. 파일 저장
            content = "\n".join(lines)
            await asyncio.to_thread(file_path.write_text, content, "utf-8")

            logger.info(f"Conversation exported: user_id={user_id}, file={file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to export conversation: user_id={user_id}, error={e}")
            return None

    async def _summarize_conversation(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        세션 대화를 LLM으로 요약

        Args:
            user_id: 유저 ID

        Returns:
            요약 Dict (topics, emotional_journey, key_points, next_session_notes, overall_mood)
            실패 시 None
        """
        try:
            # 1. 세션 조회
            session = await self.store.get(user_id)
            if not session:
                logger.warning(f"No session to summarize: user_id={user_id}")
                return None

            if not session.conversation_history or len(session.conversation_history) < 2:
                logger.warning(f"Conversation too short to summarize: user_id={user_id}")
                return None

            # 2. 세션 시간 계산
            duration = now_kst() - session.session_started_at
            duration_minutes = int(duration.total_seconds() / 60)

            # 3. 대화 히스토리 포맷팅
            conversation_text = []
            for turn in session.conversation_history:
                speaker = "사용자" if turn.role == "user" else "사만다"
                conversation_text.append(f"{speaker}: {turn.content}")

            # 4. LLM 프롬프트 구성
            from app.engine.prompts import SUMMARY_SYSTEM_PROMPT
            from app.integrations.llm.gemini_provider import GeminiProvider
            from app.integrations.llm.base import GenerationConfig

            full_prompt = f"""{SUMMARY_SYSTEM_PROMPT}

[대화 히스토리]
{chr(10).join(conversation_text)}

[세션 정보]
- 진행 시간: {duration_minutes}분
- 총 턴 수: {len(session.conversation_history)}

위 대화를 분석하여 JSON 형식으로 요약해주세요.
"""

            # 5. Gemini 호출
            llm = GeminiProvider()
            config = GenerationConfig(temperature=0.3)
            summary = await llm.generate_structured(full_prompt, config)

            # 7. 세션 시간 추가
            summary["session_duration_minutes"] = duration_minutes
            summary["session_date"] = session.session_started_at.strftime("%Y-%m-%d %H:%M")

            logger.info(f"Conversation summarized: user_id={user_id}, duration={duration_minutes}분")
            return summary

        except ValueError as e:
            logger.error(f"Failed to parse summary JSON: user_id={user_id}, error={e}")
            return None
        except Exception as e:
            logger.error(f"Failed to summarize conversation: user_id={user_id}, error={e}")
            return None
