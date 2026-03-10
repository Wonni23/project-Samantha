# app/models/user_context.py
from typing import Any, Optional, Dict, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from .enums import PersonaType

if TYPE_CHECKING:
    from .user import User

class UserContext(SQLModel, table=True):
    # 테이블명을 클래스명과 맞춰 'user_context'로 변경했습니다. (기존 persona_states 대체)
    __tablename__ = "user_context"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    
    # [1. AI Persona]
    current_persona: PersonaType = Field(default=PersonaType.SIA_FEMALE)
    user_title: str = Field(default="선생님")

    # 5-Axis Weights (0.0 ~ 1.0)
    axis_playful: float = Field(default=0.5)
    axis_feisty: float = Field(default=0.2)
    axis_dependent: float = Field(default=0.2)
    axis_caregive: float = Field(default=0.5)
    axis_reflective: float = Field(default=0.1)
    
    # [2. User Profile]
    # 신상 정보 (가족, 건강, 취향, 인간관계 등)
    user_profile: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # [3. Memory & Context] (I-01 단기기억 & L-01 퀘스트)
    # RDBMS에 저장되는 '저번 세션 요약본' (JSON)
    last_summary: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    # 생애 퀘스트 진척도 (JSON)
    legacy_progress: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # [4. Visual State] - 현재 착용 중인 아이템 상태 (JSON)
    # 프론트엔드(Live2D)는 이 JSON을 보고 아바타를 그립니다.
    # 구조 예시:
    # {
    #   "outfit": "item_id_101",   (한복)
    #   "head": null,              (모자 안 씀)
    #   "hand": "item_id_505",     (꽃 들고 있음)
    #   "background": "item_id_900" (기와집 배경)
    # }
    avatar_state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # 터치 반응 스크립트 버전 (클라이언트 동기화용)
    touch_script_version: int = Field(default=1)

    user: Optional["User"] = Relationship(back_populates="state")