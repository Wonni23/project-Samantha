# app/models/quest.py
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from .enums import QuestType, QuestStatus

if TYPE_CHECKING:
    from .user import User

# [Quest Menu] - 개발자나 운영자가 등록하는 퀘스트 원본
class QuestDefinition(SQLModel, table=True):
    __tablename__ = "quest_definitions"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 퀘스트 타입: PEDOMETER(만보기), PHOTO(인증샷), LOCATION(장소방문), INTERACTION(대화)
    type: QuestType = Field(index=True)
    
    title: str          # "봄꽃 구경 시켜주기"
    description: str    # "시아가 꽃을 보고 싶어해요. 길가에 핀 꽃을 찍어주세요."
    
    # [Clear Condition] - 검증 로직을 위한 메타데이터
    # 예: {"target_steps": 500} 또는 {"vision_keyword": ["flower", "dandelion"]}
    target_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # [Reward] - 보상 (도파민)
    # 예: {"intimacy": 5, "avatar_item": "hand_flower_01", "item_duration_hours": 24}
    reward_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    logs: List["QuestLog"] = Relationship(back_populates="definition")


# [User Quest History] - 유저가 수행 중이거나 완료한 기록
class QuestLog(SQLModel, table=True):
    __tablename__ = "quest_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: int = Field(foreign_key="users.id", index=True)
    quest_id: int = Field(foreign_key="quest_definitions.id")
    
    status: QuestStatus = Field(default=QuestStatus.IN_PROGRESS) # IN_PROGRESS, COMPLETED, FAILED
    
    # [Evidence] - B2G 증빙용 (사진 URL, 달성 시 걸음 수 등)
    proof_data: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
    # 예: {"image_url": "s3://...", "detected_labels": ["dandelion"]}
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="quest_logs")
    definition: Optional["QuestDefinition"] = Relationship(back_populates="logs")