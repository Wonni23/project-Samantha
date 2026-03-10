# app/core/security.py
from datetime import datetime, timedelta
from typing import Union, Any, Optional
from jose import jwt, JWTError
import bcrypt
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Access Token 생성"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: Union[str, Any]) -> str:
    """Refresh Token 생성"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError, UnicodeDecodeError) as e:
        logger.warning(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_access_token(token: str) -> Optional[int]:
    """
    [추가] Access Token 검증 및 user_id 추출
    :param token: JWT String
    :return: user_id (int) or None (Invalid)
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # 토큰 타입 확인
        if payload.get("type") != "access":
            return None
            
        user_id = payload.get("sub")
        if user_id is None:
            return None
            
        return int(user_id)
        
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None
