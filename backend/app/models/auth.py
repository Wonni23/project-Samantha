# app/models/auth.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String
from .enums import PlatformType

if TYPE_CHECKING:
    from .user import User

# ==========================================
# 1. SocialAccount: 카카오/네이버/구글 연동
# User 1명에게 여러 소셜 계정이 붙을 수 있음 (확장성)
# ==========================================
class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    # provider: "kakao", "naver", "google"
    provider: str = Field(index=True) 
    
    # social_id: 제공업체에서 주는 고유 ID (sub값)
    # ex: "123456789" (카카오 회원번호)
    social_id: str = Field(index=True)
    
    # email: 소셜에서 받아온 이메일 (계정 복구용)
    email: Optional[str] = Field(default=None)
    
    # (선택) 엑세스 토큰 저장 (나중에 카카오톡 메시지 보내기 기능용)
    access_token: Optional[str] = Field(default=None, nullable=True)
    refresh_token: Optional[str] = Field(default=None, nullable=True)
    
    connected_at: datetime = Field(default_factory=datetime.now)

    user: Optional["User"] = Relationship(back_populates="social_accounts")


# ==========================================
# 2. AuthSession: JWT Refresh Token 저장소
# "어? 나 해킹당했나?" 할 때 기기별로 로그아웃 시키기 위함
# ==========================================
class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Refresh Token 값 (해싱해서 넣는 게 정석이나, MVP에선 원본 저장 후 만료 체크)
    refresh_token: str = Field(sa_column=Column(String(512), index=True))
    
    # 메타 데이터 (어디서 로그인했나)
    client_ip: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None) # "Android 14 / SM-S908N"
    
    expires_at: datetime # 토큰 만료 시간
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 강제 만료 여부 (True면 해당 토큰으로 갱신 불가)
    is_revoked: bool = Field(default=False)

    user: Optional["User"] = Relationship(back_populates="sessions")