# app/engine/memory.py
"""
벡터 검색 전용 (pgvector 활용)
하이브리드 검색 (벡터 + 키워드) 지원
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from kiwipiepy import Kiwi
from app.core.config import settings
from app.integrations.llm.openai_provider import OpenAIEmbeddingProvider
from app.models.enums import LegacyCategory

if TYPE_CHECKING:
    from app.models.content import LifeLegacy

logger = logging.getLogger(__name__)


# ==================== 상수 (Config에서 참조) ====================

# 하위 호환성을 위해 모듈 레벨 상수 유지 (settings 참조)
MAX_IMPORTANCE = settings.RAG_MAX_IMPORTANCE
IMPORTANCE_WEIGHT = settings.RAG_IMPORTANCE_WEIGHT
DUPLICATE_THRESHOLD = settings.RAG_DUPLICATE_THRESHOLD


# ==================== Kiwi 싱글톤 ====================

_kiwi_instance: Optional[Kiwi] = None


def get_kiwi() -> Kiwi:
    """
    Kiwi 형태소 분석기 싱글톤

    Kiwi 인스턴스 생성 시 모델 로딩 비용이 크므로
    싱글톤으로 한 번만 생성하여 재사용
    """
    global _kiwi_instance
    if _kiwi_instance is None:
        _kiwi_instance = Kiwi()
    return _kiwi_instance


# ==================== MemoryEngine 싱글톤 ====================

_memory_engine_instance: Optional["MemoryEngine"] = None


def get_memory_engine() -> "MemoryEngine":
    """
    MemoryEngine 싱글톤 팩토리

    OpenAI AsyncClient 내부의 httpx 커넥션 풀을 서버 수명 동안 유지하여
    첫 요청 TCP+TLS 핸드셰이크 비용(~800ms)을 제거.
    """
    global _memory_engine_instance
    if _memory_engine_instance is None:
        _memory_engine_instance = MemoryEngine()
    return _memory_engine_instance


# ==================== MemoryEngine ====================


class MemoryEngine:
    """
    RAG 엔진
    임베딩 생성 및 벡터 검색만 처리
    """

    # 품사 기반 가중치
    POS_WEIGHTS = {
        'NNP': 1.0,   # 고유명사
        'NNG': 0.9,   # 일반명사
        'VV': 0.7,    # 동사
        'VA': 0.7,    # 형용사
        'XR': 0.6,    # 어근
    }

    # 하이브리드 검색 가중치 (Config에서 참조)
    VECTOR_WEIGHT = settings.RAG_VECTOR_WEIGHT
    KEYWORD_WEIGHT = settings.RAG_KEYWORD_WEIGHT

    def __init__(self):
        self.embedding_provider = OpenAIEmbeddingProvider()
        self.kiwi = get_kiwi()  # 한국어 형태소 분석기 (싱글톤)

    async def get_embedding(self, text: str) -> List[float]:
        """
        텍스트의 임베딩 벡터를 생성

        Args:
            text: 입력 텍스트

        Returns:
            1536차원 임베딩 벡터 (OpenAI text-embedding-3-small)

        Raises:
            ValueError: 텍스트가 비어있거나 너무 긴 경우
        """
        if not text or not isinstance(text, str):
            raise ValueError("text는 비어있지 않은 문자열이어야 합니다")

        text = text.strip()
        if not text:
            raise ValueError("text는 공백만으로 구성될 수 없습니다")

        max_len = settings.EMBEDDING_TEXT_MAX_LENGTH
        if len(text) > max_len:
            raise ValueError(f"text 길이가 {max_len}자를 초과합니다: {len(text)}자")

        return await self.embedding_provider.get_embedding(text)

    async def search_memory_hybrid(
        self,
        db: AsyncSession,
        query_text: str,
        user_id: int,
        categories: Optional[List[LegacyCategory]] = None,
        vector_threshold: float = 0.65,
        top_k: int = 30,
        final_limit: int = 5,
        min_keyword_score: float = 0.0,
        conversation_history: Optional[List[str]] = None,
    ) -> List[LifeLegacy]:
        """
        하이브리드 검색: 벡터 검색 + 키워드 매칭 + importance 가중치 + 대화 맥락

        1단계: 벡터 검색으로 Top-K 후보 추출 (threshold 완화)
        2단계: 키워드 매칭 점수 계산
        3단계: importance 가중치 + 대화 맥락 부스트 적용
        4단계: 최소 키워드 점수 필터링
        5단계: 최종 Top-N 반환

        Args:
            db: 데이터베이스 세션
            query_text: 검색 쿼리 텍스트
            user_id: 사용자 ID
            categories: 검색 대상 카테고리 (None이면 전체)
            vector_threshold: 벡터 검색 임계값 (기본 0.65, 코사인 거리)
            top_k: 벡터 검색 단계에서 가져올 후보 개수 (기본 30)
            final_limit: 최종 반환할 결과 개수 (기본 5)
            min_keyword_score: 최소 키워드 점수 (이 점수 미만은 제외, 기본 0.0)
            conversation_history: 최근 대화 이력 (user 발화만, 최근 3~5턴)

        Returns:
            하이브리드 점수로 정렬된 LifeLegacy 객체 리스트
        """
        if not query_text or not query_text.strip():
            return []

        # Phase 1: 무의미 쿼리 차단
        if self._is_meaningless_query(query_text):
            return []

        # Phase 1: 쿼리 품질 기반 동적 threshold
        effective_threshold = self._calculate_dynamic_threshold(
            query_text, conversation_history, vector_threshold
        )

        # 1단계: 벡터 검색으로 Top-K 후보 추출
        query_embedding = await self.get_embedding(query_text)
        vector_candidates = await self._vector_search_candidates(
            db, query_embedding, user_id, effective_threshold, top_k,
            categories=categories,
        )

        if not vector_candidates:
            return []

        # 2단계: 키워드 추출
        query_keywords = self._extract_keywords(query_text)

        # 3단계: 하이브리드 점수 계산 및 재정렬
        scored_results = []
        for candidate, vector_distance in vector_candidates:
            keyword_score = self._calculate_keyword_score(
                query_keywords, candidate.summary
            )

            # 최소 키워드 점수 필터링 (관련성 없는 결과 제외)
            if keyword_score < min_keyword_score:
                continue

            # 하이브리드 점수 계산
            # 벡터 유사도: 거리 -> 유사도 변환 (0~1)
            vector_similarity = max(0, 1 - vector_distance)

            # importance 정규화 (0~1)
            importance_norm = candidate.importance / MAX_IMPORTANCE

            # Phase 1: 동적 가중치 적용
            vector_weight, keyword_weight = self._calculate_dynamic_weights(
                query_text, query_keywords
            )

            # 기본 점수: 벡터 + 키워드 (합계 = 1.0)
            base_score = (
                vector_similarity * vector_weight
                + keyword_score * keyword_weight
            )

            # importance 승법 보너스 (최대 +15% 부스트)
            importance_boost = base_score * importance_norm * IMPORTANCE_WEIGHT

            # Phase 1: 대화 맥락 부스트 (조건부 적용, 최대 +0.4)
            context_boost = self._calculate_context_boost(
                candidate.summary,
                conversation_history,
                query_keywords  # 무의미 쿼리 차단용
            )

            # 최종 점수 = 기본 점수 + importance 보너스 + 맥락 보너스
            hybrid_score = base_score + importance_boost + context_boost

            scored_results.append((candidate, hybrid_score, keyword_score, vector_similarity))

        # 4단계: 하이브리드 점수로 정렬
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # 5단계: 최종 결과 반환
        return [candidate for candidate, _, _, _ in scored_results[:final_limit]]

    async def _vector_search_candidates(
        self,
        db: AsyncSession,
        embedding: List[float],
        user_id: int,
        threshold: float,
        limit: int,
        categories: Optional[List[LegacyCategory]] = None,
    ) -> List[Tuple[LifeLegacy, float]]:
        """
        벡터 검색으로 후보 추출 (거리값 포함)

        Args:
            db: 데이터베이스 세션
            embedding: 쿼리 임베딩 벡터
            user_id: 사용자 ID
            threshold: 코사인 거리 임계값 (낮을수록 엄격)
            limit: 반환할 최대 후보 수
            categories: 검색 대상 카테고리 (None이면 전체)

        Returns:
            (LifeLegacy 객체, 코사인 거리) 튜플의 리스트
            정렬: (distance ASC, importance DESC)
        """
        try:
            from app.models.content import LifeLegacy

            # 거리값을 함께 가져오기 위해 select에 distance 추가
            distance_expr = LifeLegacy.embedding.cosine_distance(embedding)

            # 기본 조건: 유저별 분리 + 거리 임계값 + importance >= 0
            conditions = [
                LifeLegacy.user_id == user_id,
                distance_expr <= threshold,
                LifeLegacy.importance >= 0,  # 삭제 마킹(-1) 제외
            ]

            # 카테고리 필터 (지정된 경우만)
            if categories:
                conditions.append(LifeLegacy.category.in_(categories))

            # 정렬: 거리 오름차순 (가까울수록 우선), importance 내림차순 (높을수록 우선)
            statement = (
                select(LifeLegacy, distance_expr)
                .where(*conditions)
                .order_by(distance_expr, LifeLegacy.importance.desc())
                .limit(limit)
            )

            result = await db.execute(statement)
            return result.all()

        except ValueError as e:
            logger.warning(f"Vector search - invalid input: {e}")
            return []
        except Exception as e:
            logger.error(f"Vector candidate search error: {e}", exc_info=True)
            return []

    async def find_duplicate_legacy(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        embedding: List[float],
        category: LegacyCategory,
        threshold: float = DUPLICATE_THRESHOLD,
    ) -> Optional[LifeLegacy]:
        """
        중복 메모리 검색 (저장 전 중복 체크용)

        동일 category 내에서 distance 가장 가까운 1개 반환.
        정렬: distance ASC만 (importance 무시)

        Args:
            db: 데이터베이스 세션
            user_id: 유저 ID
            embedding: 새 메모리의 임베딩
            category: 동일 카테고리 내에서만 검색
            threshold: 코사인 거리 임계값 (기본 0.15 = 85% 유사)

        Returns:
            가장 유사한 LifeLegacy (없으면 None)
        """
        from app.models.content import LifeLegacy

        distance_expr = LifeLegacy.embedding.cosine_distance(embedding)

        statement = (
            select(LifeLegacy)
            .where(
                LifeLegacy.user_id == user_id,
                LifeLegacy.category == category,
                LifeLegacy.importance >= 0,  # 삭제 마킹 제외
                distance_expr <= threshold,
            )
            .order_by(distance_expr)
            .limit(1)
        )

        result = await db.execute(statement)
        return result.scalar_one_or_none()

    def _extract_keywords(self, text: str) -> Dict[str, float]:
        """
        Kiwi 형태소 분석기를 사용한 키워드 추출 (품사 기반 가중치)

        Args:
            text: 입력 텍스트

        Returns:
            {키워드: 가중치} 딕셔너리
            - 고유명사(NNP): 1.0
            - 일반명사(NNG): 0.9
            - 동사/형용사(VV/VA): 0.7
            - 어근(XR): 0.6
        """
        result = self.kiwi.tokenize(text)
        weighted_keywords: Dict[str, float] = {}

        # 의미 있는 품사만 추출
        target_tags = {'NNG', 'NNP', 'VV', 'VA', 'XR'}

        # 불용어 (의미 없는 일반적인 단어)
        stop_words = {'것', '수', '등', '이', '그', '저'}

        for token in result:
            if token.tag not in target_tags:
                continue

            form = token.form

            # 불용어 제외
            if form in stop_words:
                continue

            # 길이 조건: 명사는 1글자 허용, 동사/형용사/어근은 2글자 이상
            if token.tag in {'NNG', 'NNP'}:
                if len(form) < 1:
                    continue
            elif len(form) < 2:
                continue

            # 품사별 가중치 적용 (이미 존재하면 더 높은 가중치 유지)
            weight = self.POS_WEIGHTS.get(token.tag, 0.6)
            if form not in weighted_keywords or weighted_keywords[form] < weight:
                weighted_keywords[form] = weight

        return weighted_keywords

    def _calculate_keyword_score(
        self,
        query_keywords: Dict[str, float],
        target_text: str
    ) -> float:
        """
        가중치 기반 키워드 매칭 점수 계산

        Args:
            query_keywords: {키워드: 가중치} 딕셔너리
            target_text: 대상 텍스트

        Returns:
            0.0 ~ 1.0 사이의 키워드 매칭 점수
        """
        if not query_keywords:
            return 0.0

        # 대상 텍스트는 확장 없이 원본 키워드만 추출
        # (타겟은 이미 저장된 메모리이므로 확장 불필요, 쿼리만 확장하면 됨)
        target_keywords = self._extract_keywords(target_text)

        if not target_keywords:
            return 0.0

        # 가중치 기반 매칭 점수 계산
        # 쿼리 키워드가 타겟에 있을 때 (쿼리 가중치 * 타겟 가중치) 합산
        matched_score = 0.0
        max_possible_score = sum(query_keywords.values())

        for query_kw, query_weight in query_keywords.items():
            # 정확 매칭
            if query_kw in target_keywords:
                matched_score += query_weight * target_keywords[query_kw]
            else:
                # 부분 매칭 (어간 포함)
                for target_kw, target_weight in target_keywords.items():
                    if len(query_kw) >= 2 and len(target_kw) >= 2:
                        if query_kw in target_kw or target_kw in query_kw:
                            matched_score += query_weight * target_weight * 0.7  # 부분 매칭 감점
                            break

        # 정규화 (0~1 범위)
        if max_possible_score > 0:
            return min(1.0, matched_score / max_possible_score)
        return 0.0


    def _is_meaningless_query(self, query: str) -> bool:
        """
        통계적/규칙 기반 무의미 쿼리 판별 (하드코딩 없음)

        Args:
            query: 검색 쿼리

        Returns:
            True if 무의미 쿼리 (검색 차단해야 함)
        """
        # 1. 키워드 추출 결과 확인
        keywords = self._extract_keywords(query)

        # 키워드 0개 → 무의미
        if len(keywords) == 0:
            return True

        # 2. 품사 분석: 의미 있는 품사 확인
        meaningful_pos = set()
        for token in self.kiwi.tokenize(query):
            # NNG(일반명사), NNP(고유명사), VV(동사), VA(형용사)만 의미 있음
            if token.tag in ['NNG', 'NNP', 'VV', 'VA']:
                meaningful_pos.add(token.form)

        # 의미 있는 품사 0개 → 무의미 (감탄사, 대명사만 있음)
        if len(meaningful_pos) == 0:
            return True

        # 3. 고가중치 키워드 확인 (0.7 이상)
        high_quality = [k for k, w in keywords.items() if w >= 0.7]

        # 고가중치 키워드 0개 + 쿼리 짧음 → 무의미
        if len(high_quality) == 0 and len(query.strip()) <= 3:
            return True

        return False

    def _calculate_dynamic_threshold(
        self,
        query_text: str,
        conversation_history: Optional[List[str]],
        base_threshold: float = 0.65
    ) -> float:
        """
        쿼리 품질 기반 동적 threshold 계산

        Args:
            query_text: 검색 쿼리
            conversation_history: 대화 맥락
            base_threshold: 기본 threshold (기본 0.65)

        Returns:
            동적 조정된 threshold
        """
        # 1. 맥락 없으면 기본값
        if not conversation_history or len(conversation_history) == 0:
            return base_threshold

        # 2. 키워드 품질 분석
        keywords = self._extract_keywords(query_text)

        # 고가중치 키워드 (0.7 이상)
        high_quality = [k for k, w in keywords.items() if w >= 0.7]

        # 3. 동적 조정
        if len(high_quality) >= 2:
            # 명확한 쿼리 + 맥락 → 매우 완화
            return min(0.90, base_threshold + 0.25)  # 0.90
        elif len(high_quality) >= 1:
            # 보통 쿼리 + 맥락 → 완화
            return min(0.85, base_threshold + 0.20)  # 0.85
        else:
            # 약한 쿼리 + 맥락 → 약간 완화
            return min(0.75, base_threshold + 0.10)  # 0.75

    def _calculate_dynamic_weights(
        self,
        query_text: str,
        keywords: Dict[str, float]
    ) -> tuple[float, float]:
        """
        쿼리 길이/품질에 따른 동적 가중치 계산

        Args:
            query_text: 검색 쿼리
            keywords: 추출된 키워드

        Returns:
            (vector_weight, keyword_weight) 튜플
        """
        # 긴 쿼리 (4+ 토큰) → 키워드 중시
        if len(query_text.split()) >= 4:
            return 0.2, 0.8  # vector 20%, keyword 80%

        # 보통 쿼리 (2-3 토큰) + 키워드 있음 → 균형
        if len(keywords) >= 1:
            return 0.4, 0.6  # vector 40%, keyword 60%

        # 짧은 쿼리 (1 토큰) → 벡터 중시
        return 0.6, 0.4  # vector 60%, keyword 40%

    def _calculate_context_boost(
        self,
        candidate_summary: str,
        conversation_history: Optional[List[str]] = None,
        query_keywords: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        대화 맥락 기반 부스트 계산 (가산 보너스, 조건부 적용)

        최근 대화 이력의 키워드가 Legacy summary에 포함되면 보너스 부여.
        모호한 쿼리("해운대에서 있었던 일")를 이전 맥락("아내 순자")으로 해결.

        **Phase 1 개선**: 쿼리가 무의미하면 Context Boost 차단

        Args:
            candidate_summary: Legacy summary 텍스트
            conversation_history: 최근 대화 이력 (user 발화만, 최근 3~5턴)
            query_keywords: 쿼리 키워드 (무의미 쿼리 판별용)

        Returns:
            대화 맥락 부스트 (0.0 ~ 0.4)

        Example:
            턴1: "아내 순자 생각나네" → keywords: {아내, 순자}
            턴2: "해운대에서 있었던 일" (모호)
            → Legacy "아내 박순자... 해운대" 에 부스트!
        """
        # Phase 1: 쿼리가 무의미하면 Context Boost 차단
        if query_keywords is not None and len(query_keywords) == 0:
            return 0.0

        if not conversation_history or len(conversation_history) == 0:
            return 0.0

        # 최근 3턴에서 키워드 추출 (너무 오래된 맥락은 제외)
        history_keywords = {}
        for turn in conversation_history[-3:]:
            keywords = self._extract_keywords(turn)
            history_keywords.update(keywords)

        if not history_keywords:
            return 0.0

        # Legacy summary 키워드 추출
        summary_keywords = self._extract_keywords(candidate_summary)

        # Phase 1: 고가중치만 사용 (0.7 이상)
        important_history = {k: v for k, v in history_keywords.items() if v >= 0.7}
        important_summary = {k: v for k, v in summary_keywords.items() if v >= 0.7}

        if not important_history:
            return 0.0

        # Phase 2: 토픽 연속성 감지 — 쿼리 키워드와 히스토리 키워드 겹침 확인
        # 쿼리에 고품질 키워드가 있는데 히스토리와 겹침 0 → 토픽 전환 → 부스트 감쇠
        topic_changed = False
        if query_keywords:
            query_important = {k for k, v in query_keywords.items() if v >= 0.7}
            if query_important and not (query_important & set(important_history.keys())):
                topic_changed = True

        # 매칭 키워드 계산
        matched_keywords = set(important_history.keys()) & set(important_summary.keys())

        if matched_keywords:
            # Phase 1: 가중치 반영한 매칭 점수
            match_score = sum(
                important_history[k] * important_summary[k] for k in matched_keywords
            )
            match_ratio = match_score / sum(important_history.values())

            if topic_changed:
                # 토픽 전환 시 부스트 대폭 감쇠 (최대 0.1)
                return min(0.1, match_ratio * 0.15)

            # Phase 1: 최대 +0.4 (기존 +0.2에서 2배 증가)
            return min(0.4, match_ratio * 0.6)

        return 0.0
