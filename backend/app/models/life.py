# app/models/life.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, time
from sqlmodel import Field, SQLModel, Relationship
from .enums import RoutineType

if TYPE_CHECKING:
    from .user import User

class Routine(SQLModel, table=True):
    __tablename__ = "routines"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # 루틴 종류: MEDICATION(약), MEAL(식사), EXERCISE(운동), SLEEP(수면)
    type: str = Field(index=True) 
    title: str # "고혈압 약", "점심 식사"
    
    # 알림 시간 (ex: 08:30:00)
    trigger_time: time = Field(index=True)
    
    # 반복 요일 (Bitmask or JSON list) -> MVP에선 "매일(Daily)" 가정하고 생략 가능하나,
    # "월,수,금 투석" 같은 게 있을 수 있으므로 String으로 저장 (ex: "MON,WED,FRI")
    repeat_days: str = Field(default="ALL") 
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    user: Optional["User"] = Relationship(back_populates="routines")