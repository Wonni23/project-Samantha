from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException

from app.models.user import User
from app.models.user_context import UserContext
from app.models.auth import SocialAccount, AuthSession
from app.models.terms import TermsAgreement
from app.schemas.auth_schema import ProfileSetupRequest, TermsAgreeRequest, TokenResponse, LocalRegisterRequest, LocalLoginRequest
from app.core import security, exceptions
from app.core.config import settings
from app.integrations.notification.fcm_client import OAuthClient

class AuthService:
    """인증 관련 비즈니스 로직 집합"""

    @staticmethod
    async def login_social(db: AsyncSession, provider: str, code: str, redirect_uri: Optional[str] = None, state: Optional[str] = None, client_ip: str = "unknown", user_agent: str = "unknown") -> TokenResponse:
        """
        소셜 로그인 처리
        1. Provider에게 Code로 AccessToken 요청 -> User Info 획득
        2. DB에 User/SocialAccount 존재 확인
        3. 없으면 생성 (회원가입)
        4. JWT 토큰 발급
        """
        # 1. 소셜 유저 정보 가져오기
        user_info = await OAuthClient.get_user_info(provider, code, redirect_uri, state)
        
        social_id = user_info["social_id"]
        email = user_info.get("email")
        
        # [수정] execute() 사용 및 scalars().first()로 결과 추출
        stmt = select(SocialAccount).where(
            SocialAccount.provider == provider, 
            SocialAccount.social_id == social_id
        )
        result = await db.execute(stmt)
        account = result.scalars().first()

        user = None
        
        if account:
            # 기존 유저 조회
            user = await db.get(User, account.user_id)
        else:
            # 신규 유저 생성
            # [주의] User 모델에서 gender, birth_year 등이 Optional(nullable=True)이어야 함!
            user = User(
                role="user", 
                tier="free",
                created_at=datetime.utcnow() # 생성 시간 명시 권장
            )
            db.add(user)
            await db.flush() # user.id 생성

            # 소셜 계정 연결
            new_account = SocialAccount(
                user_id=user.id,
                provider=provider,
                social_id=social_id,
                email=email,
                connected_at=datetime.utcnow()
            )
            db.add(new_account)
        
        # 2. 토큰 발급
        access_token = security.create_access_token(user.id)
        refresh_token = security.create_refresh_token(user.id)

        # 3. 리프레시 토큰 DB 저장
        # (만료일 계산 로직 보완)
        refresh_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = AuthSession(
            user_id=user.id,
            refresh_token=refresh_token,
            client_ip=client_ip, 
            user_agent=user_agent,
            expires_at=refresh_expires_at
        )
        db.add(session)
        await db.commit()

        # 4. 온보딩 완료 여부 체크
        is_complete = await AuthService.check_onboarding_status(db, user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            is_onboarding_complete=is_complete
        )

    @staticmethod
    async def register_local(db: AsyncSession, data: "LocalRegisterRequest", client_ip: str = "unknown", user_agent: str = "unknown") -> TokenResponse:
        """이메일/비밀번호 로컬 회원가입"""
        # 1. 이메일 중복 확인
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        if result.scalars().first():
            raise exceptions.AuthError.EMAIL_ALREADY_EXISTS
        
        # 2. 비밀번호 해싱 및 유저 생성
        hashed_password = security.get_password_hash(data.password)
        user = User(
            email=data.email,
            password_hash=hashed_password,
            role="user", 
            tier="free",
            created_at=datetime.utcnow()
        )
        db.add(user)
        await db.flush()

        # 3. 토큰 발급
        access_token = security.create_access_token(user.id)
        refresh_token = security.create_refresh_token(user.id)

        # 4. 세션(리프레시 토큰) 저장
        refresh_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = AuthSession(
            user_id=user.id,
            refresh_token=refresh_token,
            client_ip=client_ip, 
            user_agent=user_agent,
            expires_at=refresh_expires_at
        )
        db.add(session)
        await db.commit()

        # 방금 가입했으므로 온보딩 완료는 무조건 False
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            is_onboarding_complete=False
        )

    @staticmethod
    async def login_local(db: AsyncSession, data: "LocalLoginRequest", client_ip: str = "unknown", user_agent: str = "unknown") -> TokenResponse:
        """이메일/비밀번호 로컬 로그인"""
        # 1. 유저 조회
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        # 2. 유저 존재 여부 및 비밀번호 검증
        if not user or not user.password_hash or not security.verify_password(data.password, user.password_hash):
            raise exceptions.AuthError.CREDENTIALS_INVALID

        # 3. 토큰 발급
        access_token = security.create_access_token(user.id)
        refresh_token = security.create_refresh_token(user.id)

        # 4. 세션 저장
        refresh_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = AuthSession(
            user_id=user.id,
            refresh_token=refresh_token,
            client_ip=client_ip, 
            user_agent=user_agent,
            expires_at=refresh_expires_at
        )
        db.add(session)
        await db.commit()

        # 5. 온보딩 여부 체크
        is_complete = await AuthService.check_onboarding_status(db, user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            is_onboarding_complete=is_complete
        )

    @staticmethod
    async def setup_profile(db: AsyncSession, user_id: int, data: ProfileSetupRequest):
        user = await db.get(User, user_id)
        if not user:
            raise exceptions.AuthError.USER_NOT_FOUND
        
        user.real_name = data.real_name
        user.gender = data.gender
        user.birth_year = data.birth_year
        user.platform = data.platform
        db.add(user)

        # [수정] execute() 사용
        stmt = select(UserContext).where(UserContext.user_id == user_id)
        result = await db.execute(stmt)
        context = result.scalars().first()
        
        if not context:
            context = UserContext(user_id=user_id)
        
        context.user_title = data.user_title
        db.add(context)
        
        await db.commit()

    @staticmethod
    async def agree_terms(db: AsyncSession, user_id: int, data: TermsAgreeRequest):
        # [수정] execute() 사용
        stmt = select(TermsAgreement).where(TermsAgreement.user_id == user_id)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.terms_of_service = data.terms_of_service
            existing.privacy_policy = data.privacy_policy
            existing.voice_collection = data.voice_collection
            existing.marketing_consent = data.marketing_consent
            existing.agreed_at = datetime.utcnow()
            db.add(existing)
        else:
            agreement = TermsAgreement(
                user_id=user_id,
                terms_of_service=data.terms_of_service,
                privacy_policy=data.privacy_policy,
                voice_collection=data.voice_collection,
                marketing_consent=data.marketing_consent,
                agreed_at=datetime.utcnow()
            )
            db.add(agreement)
        
        await db.commit()

    @staticmethod
    async def check_onboarding_status(db: AsyncSession, user_id: int) -> bool:
        user = await db.get(User, user_id)
        if not user: return False
        
        # [수정] execute() 사용
        stmt = select(TermsAgreement).where(TermsAgreement.user_id == user_id)
        result = await db.execute(stmt)
        term = result.scalars().first()
        
        has_profile = (user.gender is not None and user.birth_year is not None)
        has_term = (term is not None and term.terms_of_service)
        
        return has_profile and has_term

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
        from jose import jwt, JWTError
        from app.core.config import settings
        
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            sub = payload.get("sub")
            if sub is None:
                raise exceptions.AuthError.CREDENTIALS_INVALID
            user_id = int(sub)
            token_type = payload.get("type")
            
            if token_type != "refresh":
                raise exceptions.AuthError.CREDENTIALS_INVALID
        except JWTError:
            raise exceptions.AuthError.TOKEN_EXPIRED
        
        # [수정] execute() 사용
        stmt = select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.refresh_token == refresh_token
        )
        result = await db.execute(stmt)
        session = result.scalars().first()
        
        if not session:
            raise exceptions.AuthError.CREDENTIALS_INVALID
        
        # 만료 시간 비교 (naive UTC 기준)
        now = datetime.utcnow()
        if session.expires_at < now:
             raise exceptions.AuthError.TOKEN_EXPIRED
        
        new_access_token = security.create_access_token(user_id)
        
        session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db.add(session)
        await db.commit()
        
        is_complete = await AuthService.check_onboarding_status(db, user_id)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            is_onboarding_complete=is_complete
        )
