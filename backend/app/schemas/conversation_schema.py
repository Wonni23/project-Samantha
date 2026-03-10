# app/schemas/conversation_schema.py
"""
대화 컨텍스트 + Extraction 스키마

ConversationPipeline에서 사용하는 대화 상태 추적 및 정보 추출 모델.
"""
from enum import Enum
from typing import Literal, Optional, Set

from pydantic import BaseModel, Field, field_validator


# ============ 대화 컨텍스트 ============


class ConversationPacing(str, Enum):
    """대화 페이싱 전략"""
    PROBE = "PROBE"    # 질문으로 더 깊이 파고들기
    ABSORB = "ABSORB"  # 정보 수용/공유 (질문 없이)


class ConversationContext(BaseModel):
    """이전 턴의 대화 컨텍스트"""
    topic: str = Field("", description="이전 대화 주제")
    depth_level: int = Field(1, ge=1, le=3, description="이전 깊이 레벨 (1-3)")
    turn_count: int = Field(1, ge=1, description="현재 주제에서의 턴 수")
    conversation_pacing: ConversationPacing = Field(
        ConversationPacing.PROBE,
        description="대화 페이싱 전략 (PROBE|ABSORB)"
    )
    consecutive_probe_count: int = Field(
        0, ge=0, description="연속 PROBE 횟수"
    )
    consecutive_absorb_count: int = Field(
        0, ge=0, description="연속 ABSORB 횟수"
    )


class ConversationTracker(ConversationContext):
    """대화 추적 정보 (Actor analysis 블록 출력)

    ConversationContext의 공통 필드를 상속하고,
    출력 전용 필드(is_new_topic, next_move)를 추가.
    """
    is_new_topic: bool = Field(True, description="새로운 주제 시작 여부")
    next_move: str = Field("", description="다음 대화 방향 제안")


# ============ Extraction 스키마 (per-turn fire-and-forget) ============

# 프롬프트에서 Fixed로 선언된 5개 카테고리 + fallback
VALID_PROFILE_CATEGORIES: Set[str] = {"BIO_SPEC", "FAMILY", "SOCIAL", "HEALTH_STATUS", "PREFERENCE"}
FALLBACK_CATEGORY = "GENERAL"


class ExtractedProfile(BaseModel):
    """EXTRACTION 프롬프트가 반환하는 Profile 항목

    프롬프트 스키마:
    {"item_type": "profile", "category": "FAMILY", "key": "son_name", "value": "철수 (막내아들)"}

    카테고리가 유효하지 않으면 GENERAL로 fallback.
    """
    category: str = Field(FALLBACK_CATEGORY, description="프로필 카테고리")
    key: str = Field(..., min_length=1, description="프로필 키 (snake_case)")
    value: str = Field(..., min_length=1, description="프로필 값 (한국어)")

    @field_validator('category')
    @classmethod
    def normalize_category(cls, v: str) -> str:
        if v not in VALID_PROFILE_CATEGORIES:
            return FALLBACK_CATEGORY
        return v


class ExtractedLegacy(BaseModel):
    """EXTRACTION 프롬프트가 반환하는 Legacy 항목

    프롬프트 스키마:
    {"item_type": "legacy", "legacy_type": "EPISODE", "content": "...", "importance": 4}
    """
    legacy_type: Literal["EPISODE", "VALUE"] = Field("EPISODE", description="레거시 유형")
    content: str = Field(..., min_length=1, description="레거시 내용 (3인칭)")
    importance: int = Field(1, ge=1, le=5, description="중요도 (1~5)")
