#app/api/deps.py
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import async_session_factory # db.py 또는 database.py에 정의된 세션 팩토리
from app.core.exceptions import AuthError
from app.models.user import User

# Swagger UI 인증 버튼 활성화용
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_db() -> Generator:
    """
    [Dependency] DB 세션 생성 및 종료 자동화
    """
    async with async_session_factory() as session:
        yield session

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    [Dependency] JWT 토큰에서 user_id 추출 (DB 조회 안함, 가벼운 검증)
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            raise AuthError.CREDENTIALS_INVALID
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Access Token이 아닙니다.")
            
        return int(user_id)
        
    except JWTError:
        raise AuthError.CREDENTIALS_INVALID

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
) -> User:
    """
    [Dependency] 현재 로그인한 유저 객체 반환 (DB 조회 포함)
    """
    user = await db.get(User, user_id)
    if not user:
        raise AuthError.USER_NOT_FOUND
    return user