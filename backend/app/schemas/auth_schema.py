from pydantic import BaseModel, Field, model_validator
from typing import Optional
import re
from app.models.enums import GenderType, PlatformType

# 1. 소셜 로그인 요청 DTO
class LoginRequest(BaseModel):
    provider: str = Field(..., description="소셜 제공자 (kakao, naver, google)")
    code: str = Field(..., description="OAuth 인증 코드 (Authorization Code)")
    redirect_uri: Optional[str] = Field(None, description="리다이렉트 URI (검증용)")
    state: Optional[str] = Field(None, description="OAuth State 토큰 (CSRF 방지)")

# 1-1. 로컬 로그인/가입 요청 DTO
class LocalRegisterRequest(BaseModel):
    phone_number: str = Field(..., description="휴대폰 번호 (숫자만 입력, 예: 01012345678)")
    password: str = Field(..., description="비밀번호")

    @model_validator(mode="after")
    def validate_fields(self):
        # 숫자만 10~11자리 확인
        if not re.match(r"^01[0-9]\d{7,8}$", self.phone_number):
            raise ValueError("유효하지 않은 휴대폰 번호 형식입니다. (숫자 10~11자리)")
            
        if len(self.password) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        if not re.search(r"[A-Z]", self.password):
            raise ValueError("비밀번호는 영문 대문자를 포함해야 합니다.")
        if not re.search(r"[a-z]", self.password):
            raise ValueError("비밀번호는 영문 소문자를 포함해야 합니다.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", self.password):
            raise ValueError("비밀번호는 특수문자를 포함해야 합니다.")
        return self

class LocalLoginRequest(BaseModel):
    phone_number: str = Field(..., description="휴대폰 번호")
    password: str = Field(..., description="비밀번호")

    @model_validator(mode="after")
    def validate_phone(self):
        if not re.match(r"^01[0-9]\d{7,8}$", self.phone_number):
            raise ValueError("유효하지 않은 휴대폰 번호 형식입니다.")
        return self

# 2. 토큰 응답 DTO
class TokenResponse(BaseModel):
    access_token: str = Field(..., description="API 접근용 액세스 토큰")
    refresh_token: str = Field(..., description="토큰 갱신용 리프레시 토큰")
    token_type: str = "bearer"
    user_id: int
    is_onboarding_complete: bool = Field(..., description="온보딩(프로필+약관) 완료 여부. False면 온보딩 화면으로 이동")

# 3. 온보딩 1단계: 프로필 설정 DTO
class ProfileSetupRequest(BaseModel):
    real_name: str = Field(..., min_length=1, description="사용자 실명")
    gender: GenderType = Field(..., description="성별 (male/female)")
    birth_year: int = Field(..., ge=1900, le=2026, description="출생년도")
    user_title: str = Field(default="어르신", description="AI가 부를 호칭 (예: 오빠, 누님, 선생님)")
    platform: PlatformType = Field(default=PlatformType.ANDROID)

# 4. 온보딩 2단계: 약관 동의 DTO
class TermsAgreeRequest(BaseModel):
    terms_of_service: bool = Field(..., description="[필수] 서비스 이용약관")
    privacy_policy: bool = Field(..., description="[필수] 개인정보 처리방침")
    voice_collection: bool = Field(..., description="[필수] 음성 수집 및 이용 동의")
    marketing_consent: bool = Field(default=False, description="[선택] 마케팅 정보 수신 동의")

# 5. 토큰 갱신 요청 DTO
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="갱신에 사용할 리프레시 토큰")