# app/models/content.py
import os
from typing import Any, Optional, List, Dict, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector
from .enums import ProcessingStatus, SpeakerType, LegacyCategory, RiskType

if TYPE_CHECKING:
    from .user import User

# .env에서 차원 수 가져오기
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSION", 1536))

# 1. 단순 대화 원문 로그 (Vector 없음) -> Redis에서 .txt로 추출하여 로그를 남길거면 과연 쓸 일이 있을지? 일단 두고 나중에 생각
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    speaker: SpeakerType = Field(index=True)
    content: str 
    audio_url: Optional[str] = Field(default=None) # S3 URL
    
    # [L-05] 세션 종료 시 True인 것만 추출됨
    is_consented: bool = Field(default=False, index=True) 
    
    created_at: datetime = Field(default_factory=datetime.now)
    user: Optional["User"] = Relationship(back_populates="conversations")


# 2. L-05와 L-06 사이의 중간 대기열 (Staging) #새벽 3시까지 쌓였다가 배치 처리됨
class LegacyQueue(SQLModel, table=True):
    __tablename__ = "legacy_queue"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    
    speaker: SpeakerType = Field(index=True)
    audio_url: Optional[str] = Field(default=None) # S3 URL
    raw_content: str
    meta_info: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON)) # 감정, 주제 등
    
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = Field(default=None) # 처리 완료 여부

    # 처리 상태 관리 (재시도 로직용)
    # PENDING(대기), COMPLETED(완료), FAILED(실패-재시도필요), IGNORED(무시됨)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, index=True)
    error_log: Optional[str] = Field(default=None) # 에러나면 여기에 메시지 기록

    user: Optional["User"] = Relationship(back_populates="legacy_queue_items")


# 3. 진짜 기억 (Vector 있음)
class LifeLegacy(SQLModel, table=True):
    __tablename__ = "life_legacies"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    category: LegacyCategory = Field(index=True)
    summary: str # 3인칭으로 정제된 내용
    
    # [Core] Embedding
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))

    # [NEW] 메타 정보 (JSON) - 원본 추적용
    # 예: {"source_audio": "s3://...", "source_queue_id": 123, "tags": ["가족", "여행"]}
    meta_info: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    importance: int = Field(default=1)
    is_public: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    
    user: Optional["User"] = Relationship(back_populates="legacies")


# 4. 안전 로그 (RedLine)
class SafetyLog(SQLModel, table=True):
    __tablename__ = "safety_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    risk_type: RiskType = Field(index=True)
    risk_score: float 
    detected_text: str 
    
    is_resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    user: Optional["User"] = Relationship(back_populates="safety_logs")