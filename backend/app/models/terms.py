# app/models/terms.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User

class TermsAgreement(SQLModel, table=True):
    """
    [법적 필수 테이블] 약관 동의 내역 (TermsAgreement)
    
    * 주의사항:
    1. 이 테이블은 회사를 법적 공격(개인정보법 위반 등)으로부터 방어하는 방패입니다.
    2. 헬스케어(민감정보) + AI(국외이전) + B2G/보호자(3자제공) 특성상 필수 항목이 많습니다.
    3. 약관이 개정될 경우를 대비해 version 관리가 필요합니다.
    """
    __tablename__ = "terms_agreements"

    id: Optional[int] = Field(default=None, primary_key=True)
    # unique=True 제거 권장 (약관 갱신 시 이력 관리를 위해 1:N 가능성 열어둠)
    # 현재 MVP 단계에서는 1:1로 유지하되, 추후 마이그레이션 고려.
    user_id: int = Field(foreign_key="users.id", index=True) 

    # ----------------------------------------------------------------
    # [1. 일반 필수 약관]
    # ----------------------------------------------------------------
    terms_of_service: bool = Field(default=False, description="[필수] 서비스 이용약관 동의")
    privacy_policy: bool = Field(default=False, description="[필수] 개인정보 처리방침 동의")

    # ----------------------------------------------------------------
    # [2. 특수 필수 약관 (서비스 생존용 - 이거 없으면 불법)]
    # ----------------------------------------------------------------
    # 질병, 투약 정보 등 건강 데이터를 다루려면 필수
    sensitive_info_agreement: bool = Field(default=False, description="[필수] 민감정보 처리 동의")
    
    # OpenAI/Google 등 해외 서버로 데이터 전송 시 필수
    cross_border_transfer: bool = Field(default=False, description="[필수] 개인정보 국외 이전(LLM 활용) 동의")

    # ----------------------------------------------------------------
    # [3. 제3자 제공 및 선택 약관]
    # ----------------------------------------------------------------
    # 자녀(보호자)에게 리포트 제공, 지자체 공유 시 필수
    third_party_provision: bool = Field(default=False, description="[선택/필수] 제3자(보호자/기관) 정보 제공 동의")
    
    marketing: bool = Field(default=False, description="[선택] 마케팅 정보 수신 동의 (이벤트/프로모션)")

    # ----------------------------------------------------------------
    # [4. 감사(Audit) 정보]
    # ----------------------------------------------------------------
    terms_version: str = Field(default="1.0", description="동의 시점의 약관 버전 (v1.0)")
    agreed_at: datetime = Field(default_factory=datetime.now, description="동의한 정확한 시각")
    ip_address: Optional[str] = Field(default=None, description="부정 동의 방지용 IP 기록")

    # Relationship
    user: Optional["User"] = Relationship(back_populates="terms_agreement")