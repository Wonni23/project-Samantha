# app/models/user.py
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from .enums import GenderType, PlatformType, UserRole, UserTier

if TYPE_CHECKING:
    from .user_context import UserContext
    from .auth import SocialAccount, AuthSession
    from .content import Conversation, LegacyQueue, LifeLegacy, SafetyLog
    from .finance import SubscriptionLog
    from .life import Routine
    from .terms import TermsAgreement
    from .quest import QuestLog
    from .store import UserInventory

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # [Identity]
    email: Optional[str] = Field(default=None, unique=True, index=True)
    phone_number: Optional[str] = Field(default=None, unique=True, index=True) 
    password_hash: Optional[str] = Field(default=None)
    real_name: Optional[str] = Field(default=None)
    gender: Optional[GenderType] = Field(default=None, nullable=True)
    birth_year: Optional[int] = Field(default=None, nullable=True)
    address_district: Optional[str] = Field(nullable=True)

    # [Role & Permissions]
    role: UserRole = Field(default=UserRole.USER, index=True)

    # [Economy & Tier]
    tier: UserTier = Field(default=UserTier.FREE, index=True)
    daily_usage: int = Field(default=0) # 매일 04:00 초기화
    last_usage_reset_at: datetime = Field(default_factory=datetime.now)

    # [Organization]
    organization_id: Optional[str] = Field(default=None, index=True)

    # [Meta]
    platform: PlatformType = Field(default=PlatformType.ANDROID)
    app_version: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)

    # [Network & Notification]
    fcm_token: Optional[str] = Field(default=None, index=True)
    device_model: Optional[str] = Field(default=None)

    # [Relationships]
    state: Optional["UserContext"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    
    conversations: List["Conversation"] = Relationship(back_populates="user")
    legacies: List["LifeLegacy"] = Relationship(back_populates="user")
    legacy_queue_items: List["LegacyQueue"] = Relationship(back_populates="user")
    
    routines: List["Routine"] = Relationship(back_populates="user")
    safety_logs: List["SafetyLog"] = Relationship(back_populates="user")
    
    quest_logs: List["QuestLog"] = Relationship(back_populates="user")
    inventory: List["UserInventory"] = Relationship(back_populates="user")

    subscription_logs: List["SubscriptionLog"] = Relationship(back_populates="user")
    social_accounts: List["SocialAccount"] = Relationship(back_populates="user")
    sessions: List["AuthSession"] = Relationship(back_populates="user")
    
    terms_agreement: Optional["TermsAgreement"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )

    wards: List["GuardianRelation"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "User.id==GuardianRelation.guardian_id", "lazy": "select"},
        back_populates="guardian"
    )
    guardians: List["GuardianRelation"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "User.id==GuardianRelation.ward_id", "lazy": "select"},
        back_populates="ward"
    )


class GuardianRelation(SQLModel, table=True):
    __tablename__ = "guardian_relations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    guardian_id: int = Field(foreign_key="users.id", index=True) # 자녀 ID
    ward_id: int = Field(foreign_key="users.id", index=True)     # 부모님 ID
    
    relationship_type: str = Field(default="family") # "아들", "딸", "담당자"
    is_alert_enabled: bool = Field(default=True) 
    
    created_at: datetime = Field(default_factory=datetime.now)

    guardian: "User" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "GuardianRelation.guardian_id==User.id"}
    )
    ward: "User" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "GuardianRelation.ward_id==User.id"}
    )