from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models.enums import GenderType, PlatformType, UserRole, UserTier

class UserBase(BaseModel):
    """유저 정보의 기본 구조"""
    phone_number: Optional[str] = None
    real_name: Optional[str] = None
    gender: Optional[GenderType] = None
    birth_year: Optional[int] = None
    address_district: Optional[str] = None
    platform: PlatformType = PlatformType.ANDROID

class UserRead(UserBase):
    """내 정보 조회(GET /me) 응답용 스키마"""
    id: int
    role: UserRole
    tier: UserTier
    daily_usage: int
    created_at: datetime
    last_active_at: datetime
    
    # 온보딩 완료 여부 판단을 위해 필요한 정보
    # (auth_schema.py의 TokenResponse와 일관성 유지)
    is_onboarding_complete: bool = True 

    class Config:
        from_attributes = True  # SQLModel 객체를 Pydantic으로 변환 (Pydantic v2 방식)
        # 만약 Pydantic v1을 사용 중이라면 아래를 사용하세요:
        # orm_mode = True

class UserUpdate(BaseModel):
    real_name: Optional[str] = Field(None, min_length=1)
    gender: Optional[GenderType] = None
    birth_year: Optional[int] = None

    @field_validator('birth_year')
    @classmethod
    def validate_birth_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1900 or v > current_year:
                raise ValueError(f'birth_year must be between 1900 and {current_year}')
        return v