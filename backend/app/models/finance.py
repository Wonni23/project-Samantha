# app/models/finance.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from .enums import PaymentMethod

if TYPE_CHECKING:
    from .user import User

class SubscriptionLog(SQLModel, table=True):
    __tablename__ = "subscription_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    
    amount: int
    payment_method: PaymentMethod
    
    # 효도 결제 시 입금자명
    payer_name: Optional[str] = Field(default=None) 
    
    transaction_id: str = Field(unique=True)
    status: str = Field(default="PAID") # PAID, REFUNDED, FAILED
    
    created_at: datetime = Field(default_factory=datetime.now)

    user: Optional["User"] = Relationship(back_populates="subscription_logs")