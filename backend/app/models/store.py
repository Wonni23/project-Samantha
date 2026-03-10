from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON
from sqlalchemy import Column
from .enums import ItemCategory, ItemRarity

if TYPE_CHECKING:
    from .user import User

# [1. The Shop] - 상점 진열대 (Admin이 등록)
class StoreItem(SQLModel, table=True):
    __tablename__ = "store_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # COMMON(일반), RARE(희귀), LEGENDARY(전설 - B2G 표창 등)
    rarity: ItemRarity = Field(default=ItemRarity.COMMON, index=True)
    
    # 카테고리: OUTFIT(옷), HEAD(모자), HAND(지팡이/꽃), BACKGROUND(배경), CONSUMABLE(영양제/커피)
    category: ItemCategory = Field(index=True)
    
    name: str           # "설날 한정판 색동저고리"
    description: str    # "시아가 꼬까옷을 입고 세배를 드려요."
    
    # 가격 (0원이면 이벤트 무료 배포용)
    price_amount: int = Field(default=0) 
    currency_type: str = Field(default="KRW") # KRW(현금), POINT(활동 보상)
    
    # [Asset Info] - 프론트엔드(Live2D/Unity)가 불러올 리소스 ID
    # 예: {"model_id": "sia_v2", "texture_id": "hanbok_red", "motion_group": "bow"}
    asset_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True) # 판매 중 여부 (False면 상점에서 안 보임)
    created_at: datetime = Field(default_factory=datetime.now)

    inventory_items: List["UserInventory"] = Relationship(back_populates="item")


# [2. The Closet] - 유저의 보물창고 (구매 내역)
class UserInventory(SQLModel, table=True):
    __tablename__ = "user_inventory"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: int = Field(foreign_key="users.id", index=True)
    item_id: int = Field(foreign_key="store_items.id")
    
    # 구매/획득 경로 (SHOP_PURCHASE, QUEST_REWARD, ADMIN_GIFT)
    acquisition_source: str = Field(default="SHOP_PURCHASE")
    
    # 소모품일 경우 수량 (옷은 보통 1개, 영양제는 10개 등)
    quantity: int = Field(default=1)
    
    # [Business Logic Added] 기간제 아이템을 위한 만료일
    # Null: 영구 소장 (Permanent)
    # Value: 기간제/대여 아이템 (Rental) -> 해당 날짜 지나면 사용 불가 처리
    expires_at: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.now) # 구매일

    user: Optional["User"] = Relationship(back_populates="inventory")
    item: Optional["StoreItem"] = Relationship(back_populates="inventory_items")