# backend/app/services/user_service.py
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User

class UserService:
    @staticmethod
    async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
        return await db.get(User, user_id)

user_service = UserService()
