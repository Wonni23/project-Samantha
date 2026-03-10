# backend/app/schemas/session_schema.py
"""
세션 데이터 스키마

- 5축 상태: 타입 명시 (float 0.0~1.0)
- 프로필/요약: Dict로 유연하게 처리 (스키마 미확정)
- 대화 컨텍스트: 턴 간 연속성 추적
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import now_kst, settings
from app.schemas.conversation_schema import ConversationContext, ConversationTracker

if TYPE_CHECKING:
    from app.models.user_context import UserContext


RAPPORT_PROMOTION_TOTAL_TURNS = 50


class AxisDelta(BaseModel):
    """5축 변화량 (delta)

    [구조]
    - delta: -1.0 ~ 1.0 (필수, float)
    - sub_attribute: null 또는 snake_case 문자열 (선택)
    """
    delta: float = Field(..., ge=-1.0, le=1.0, description="변화량 (-1.0 ~ 1.0)")
    sub_attribute: Optional[str] = Field(None, description="세부 속성 (snake_case, 예: humor, teasing)")

    @field_validator('delta')
    @classmethod
    def normalize_delta(cls, v: float) -> float:
        """거의 0에 가까운 값은 0으로 정규화 (부동소수점 오차)"""
        if abs(v) < 0.001:
            return 0.0
        return v


class AxisUpdates(BaseModel):
    """5축 업데이트 (모두 선택적)

    [구조]
    {
        "playful": {"delta": 0.1, "sub_attribute": "humor"},
        "feisty": {"delta": -0.05, "sub_attribute": null},
        ...
    }

    P1: 구조 검증된 타입
    """
    playful: Optional[AxisDelta] = None
    feisty: Optional[AxisDelta] = None
    dependent: Optional[AxisDelta] = None
    caregive: Optional[AxisDelta] = None
    reflective: Optional[AxisDelta] = None

    def extract_deltas(self) -> Dict[str, float]:
        """DB 저장용 순수 delta 딕셔너리 추출"""
        result = {}
        for axis_name in ["playful", "feisty", "dependent", "caregive", "reflective"]:
            axis_delta = getattr(self, axis_name, None)
            if axis_delta and axis_delta.delta != 0.0:
                result[axis_name] = axis_delta.delta
        return result


# ============ 5축 → 비언어적 표현 매핑 ============

# axis -> (expression, emotion)
_AXIS_EXPRESSION_MAP: Dict[str, Tuple[str, str]] = {
    "playful":    ("sparkle", "cheerful"),
    "feisty":     ("pout",    "sassy"),
    "dependent":  ("adore",   "adoring"),
    "caregive":   ("warm",    "tender"),
    "reflective": ("serene",  "serene"),
}


@dataclass(frozen=True)
class DerivedExpression:
    """5축 persona_state에서 도출된 비언어적 표현 (immutable)"""
    expression: str          # Live2D (sparkle|pout|adore|warm|serene)
    emotion: str             # TTS (cheerful|sassy|adoring|tender|serene)


class PersonaState(BaseModel):
    """
    5축 페르소나 상태 (현재값)

    [확정된 구조]
    - 모든 축은 float 0.0~1.0 범위
    - delta 적용 시 clamp 처리
    """

    model_config = ConfigDict(validate_assignment=True)

    playful: float = Field(0.5, ge=0.0, le=1.0, description="재미있는, 장난스러운")
    feisty: float = Field(0.2, ge=0.0, le=1.0, description="까칠한")
    dependent: float = Field(0.2, ge=0.0, le=1.0, description="의존하는, 의지하는")
    caregive: float = Field(0.5, ge=0.0, le=1.0, description="돌보는, 배려하는")
    reflective: float = Field(0.1, ge=0.0, le=1.0, description="성찰적인, 깊이 있는")

    @classmethod
    def from_user_context(cls, ctx: UserContext) -> PersonaState:
        """UserContext DB 모델에서 변환"""
        return cls(
            playful=ctx.axis_playful,
            feisty=ctx.axis_feisty,
            dependent=ctx.axis_dependent,
            caregive=ctx.axis_caregive,
            reflective=ctx.axis_reflective,
        )

    def apply_delta(self, axis: str, delta: float) -> None:
        """
        단일 축에 delta 적용 (0.0~1.0 clamp)

        Args:
            axis: "playful" | "feisty" | "dependent" | "caregive" | "reflective"
            delta: -1.0 ~ 1.0 변화량
        """
        if not hasattr(self, axis):
            return
        current = getattr(self, axis)
        new_value = max(0.0, min(1.0, current + delta))
        setattr(self, axis, new_value)

    def apply_deltas(self, deltas: Dict[str, float]) -> None:
        """
        복수 축에 delta 일괄 적용

        Args:
            deltas: {"playful": 0.1, "feisty": -0.05, ...}
        """
        for axis, delta in deltas.items():
            self.apply_delta(axis, delta)

    def to_dict(self) -> Dict[str, float]:
        """5축 상태를 딕셔너리로 반환"""
        return self.model_dump()

    def derive_expression(self, deltas: Optional[Dict[str, float]] = None) -> DerivedExpression:
        """5축 delta → 비언어적 표현 도출 (rule-based)

        이번 턴의 양수(증가) delta 중 가장 큰 축이 dominant.
        음수(감소) delta는 해당 축의 약화를 의미하므로 표현 선택에서 제외.
        양수 delta가 없거나 비어있으면 serene (기본값).
        """
        if deltas:
            pos_deltas = {k: v for k, v in deltas.items() if k in _AXIS_EXPRESSION_MAP and v > 0}
            if pos_deltas:
                dominant = max(pos_deltas, key=lambda k: pos_deltas[k])
                expression, emotion = _AXIS_EXPRESSION_MAP[dominant]
                return DerivedExpression(expression=expression, emotion=emotion)

        # fallback: 변동 없음 또는 감소만 → serene
        return DerivedExpression(expression="serene", emotion="serene")


# ============ 페르소나 프리셋 ============

PERSONA_PRESETS: Dict[str, Dict[str, Any]] = {
    "aegyo": {
        "name": "애교쟁이",
        "description": "귀엽고 애교 많은 성격. 오빠~ 언니~ 자주 사용",
        "user_title": "오빠",
        "state": {
            "playful": 0.9,
            "feisty": 0.2,
            "dependent": 0.6,
            "caregive": 0.5,
            "reflective": 0.1,
        },
    },
    "tsundere": {
        "name": "츤데레",
        "description": "겉으론 까칠하지만 속은 따뜻한 성격. 흥! 자주 사용",
        "user_title": "선생님",
        "state": {
            "playful": 0.4,
            "feisty": 0.8,
            "dependent": 0.3,
            "caregive": 0.6,
            "reflective": 0.2,
        },
    },
    "caring": {
        "name": "다정한 언니",
        "description": "따뜻하고 배려심 깊은 성격. 걱정과 위로를 잘함",
        "user_title": "동생",
        "state": {
            "playful": 0.3,
            "feisty": 0.1,
            "dependent": 0.2,
            "caregive": 0.9,
            "reflective": 0.4,
        },
    },
    "philosopher": {
        "name": "철학자",
        "description": "깊이 있고 사려 깊은 성격. 인생과 가치에 대해 이야기",
        "user_title": "친구",
        "state": {
            "playful": 0.2,
            "feisty": 0.1,
            "dependent": 0.1,
            "caregive": 0.5,
            "reflective": 0.9,
        },
    },
    "bestie": {
        "name": "절친",
        "description": "편하고 장난기 많은 친구. 반말과 농담을 자주 사용",
        "user_title": "야",
        "state": {
            "playful": 0.8,
            "feisty": 0.5,
            "dependent": 0.4,
            "caregive": 0.4,
            "reflective": 0.2,
        },
    },
    "balanced": {
        "name": "균형잡힌 (기본)",
        "description": "모든 성격이 적당히 섞인 기본 상태",
        "user_title": "선생님",
        "state": {
            "playful": 0.5,
            "feisty": 0.2,
            "dependent": 0.2,
            "caregive": 0.5,
            "reflective": 0.1,
        },
    },
}


# ============ 대화 턴 ============


class ConversationTurn(BaseModel):
    """대화 턴 (최근 20턴 유지용)"""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


# ============ 세션 데이터 ============


class SessionData(BaseModel):
    """
    세션 전체 데이터

    [확정된 구조]
    - user_id, persona_state: 타입 명시

    [유연한 구조 - Dict]
    - user_profile, last_summary: 스키마 미확정
    """

    model_config = ConfigDict(validate_assignment=True)

    user_id: int
    persona_type: str = "sia_female"
    user_title: str = "선생님"

    # 5축 현재 상태 (확정)
    persona_state: PersonaState = Field(default_factory=PersonaState)

    # 유연한 데이터 (Dict - 내부 구조 무관)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    last_summary: Dict[str, Any] = Field(default_factory=dict)

    # 대화 히스토리 (최대 20턴)
    conversation_history: List[ConversationTurn] = Field(default_factory=list)

    # 메타 정보
    session_started_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)

    # 대화 컨텍스트 (이전 턴 정보 - Task 6용)
    conversation_context: ConversationContext = Field(
        default_factory=ConversationContext
    )

    def update_conversation_context(self, tracker: Optional[ConversationTracker]) -> None:
        """
        ConversationTracker에서 다음 턴 컨텍스트 추출

        Args:
            tracker: Actor가 반환한 conversation_tracker
        """
        if tracker:
            self.conversation_context = ConversationContext(
                **tracker.model_dump(include=ConversationContext.model_fields.keys())
            )

    def get_conversation_context(self) -> ConversationContext:
        """현재 대화 컨텍스트 반환 (Actor 입력용)"""
        return self.conversation_context

    def _get_or_create_meta(self) -> Dict[str, Any]:
        """user_profile 메타 섹션(_meta) 보장"""
        meta = self.user_profile.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            self.user_profile["_meta"] = meta
        return meta

    @staticmethod
    def _to_non_negative_int(value: Any, default: int = 0) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(0, parsed)

    def increment_total_turn_count(self, increment: int = 1) -> int:
        """누적 총 턴 수 증가 + rapport_tier 자동 승격"""
        safe_increment = self._to_non_negative_int(increment, 0)
        if safe_increment == 0:
            return self._to_non_negative_int(
                self._get_or_create_meta().get("total_turn_count"),
                0,
            )

        meta = self._get_or_create_meta()
        current = self._to_non_negative_int(meta.get("total_turn_count"), 0)
        total_turn_count = current + safe_increment
        meta["total_turn_count"] = total_turn_count

        rapport_tier_raw = self.user_profile.get("rapport_tier", "STRANGER")
        rapport_tier = (
            rapport_tier_raw.strip().upper()
            if isinstance(rapport_tier_raw, str)
            else "STRANGER"
        )
        if total_turn_count >= RAPPORT_PROMOTION_TOTAL_TURNS and rapport_tier != "FAMILY":
            self.user_profile["rapport_tier"] = "FAMILY"

        return total_turn_count

    def add_turn(self, role: Literal["user", "assistant"], content: str) -> None:
        """대화 턴 추가 (최대 MAX_HISTORY_TURNS 유지)"""
        if role == "user":
            self.increment_total_turn_count()
        self.conversation_history.append(
            ConversationTurn(role=role, content=content, timestamp=now_kst())
        )
        max_turns = settings.MAX_HISTORY_TURNS
        if len(self.conversation_history) > max_turns:
            self.conversation_history = self.conversation_history[-max_turns:]
        self.last_active_at = now_kst()

    def update_profile(self, category: str, new_info: Dict[str, Any]) -> None:
        """
        프로필 Nested Dict 구조로 병합 (중복 key는 리스트로 누적)

        구조: {
            "FAMILY": {"son_name": "철수", "daughter_age": 30},
            "HEALTH_STATUS": {"chronic": "당뇨"},
            "PREFERENCE": {"hobby": ["고양이 사진 보기", "강아지 사진 보기"]},
            ...
        }

        Args:
            category: ProfileCategory (BIO_SPEC, FAMILY, SOCIAL, HEALTH_STATUS, PREFERENCE)
            new_info: {key: value} 형태의 정보
        """
        if not category or not new_info:
            return

        if category not in self.user_profile:
            self.user_profile[category] = {}

        # 같은 key가 있으면 리스트로 누적
        for key, value in new_info.items():
            if key in self.user_profile[category]:
                existing = self.user_profile[category][key]
                # 기존 값이 리스트면 append, 아니면 리스트로 변환
                if isinstance(existing, list):
                    if value not in existing:  # 중복 방지
                        existing.append(value)
                else:
                    if existing != value:  # 같은 값이 아니면 리스트로
                        self.user_profile[category][key] = [existing, value]
            else:
                self.user_profile[category][key] = value

    def get_history_as_messages(self) -> List[Dict[str, str]]:
        """Actor 입력용 메시지 리스트 반환"""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.conversation_history
        ]
