#app/api/v1/auth.py
from fastapi import APIRouter, Depends, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api.deps import get_db, get_current_user_id
from app.schemas.auth_schema import (
    LoginRequest, TokenResponse, ProfileSetupRequest, TermsAgreeRequest, RefreshTokenRequest,
    LocalRegisterRequest, LocalLoginRequest
)
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register/local", response_model=TokenResponse, summary="로컬 아이디(이메일) 회원가입")
async def register_local(
    request: LocalRegisterRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "unknown")
    return await AuthService.register_local(db, request, client_ip, user_agent)

@router.post("/login/local", response_model=TokenResponse, summary="로컬 아이디(이메일) 로그인")
async def login_local(
    request: LocalLoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "unknown")
    return await AuthService.login_local(db, request, client_ip, user_agent)

@router.post("/login", response_model=TokenResponse, summary="소셜 로그인 (Kakao/Naver/Google)")
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    프론트엔드에서 받은 Code로 로그인을 수행하고 토큰을 발급합니다.
    - 신규 유저: 회원가입 처리 후 is_onboarding_complete=False 반환
    - 기존 유저: 로그인 처리
    """
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "unknown")
    return await AuthService.login_social(db, request.provider, request.code, request.redirect_uri, request.state, client_ip, user_agent)

@router.post("/profile", status_code=status.HTTP_200_OK, summary="[온보딩] 1. 프로필 설정")
async def setup_profile(
    request: ProfileSetupRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입 후 필수 프로필 정보(실명, 성별, 생년월일, 호칭)를 저장합니다.
    """
    await AuthService.setup_profile(db, user_id, request)
    return {"message": "프로필 설정이 완료되었습니다."}

@router.post("/terms", status_code=status.HTTP_200_OK, summary="[온보딩] 2. 약관 동의")
async def agree_terms(
    request: TermsAgreeRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    서비스 이용 약관 및 음성 수집 동의 내역을 저장합니다.
    """
    await AuthService.agree_terms(db, user_id, request)
    return {"message": "약관 동의가 완료되었습니다."}

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """리프레시 토큰으로 액세스 토큰 갱신"""
    return await AuthService.refresh_access_token(db, request.refresh_token)
