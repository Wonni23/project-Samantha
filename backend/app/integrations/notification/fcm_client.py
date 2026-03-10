#app/integrations/notification/fcm_client.py
import httpx
from fastapi import HTTPException
from app.core.config import settings

class OAuthClient:
    """
    외부 OAuth Provider(카카오, 네이버, 구글)와 통신하는 전용 클라이언트
    """
    
    @staticmethod
    async def get_user_info(provider: str, code: str, redirect_uri: str = None, state: str = None) -> dict:
        """
        [Flow]
        1. Access Token 발급
        2. 사용자 정보 요청
        """
        async with httpx.AsyncClient() as client:
            # 1단계: 토큰 발급 (Access Token)
            token = await OAuthClient._fetch_token(client, provider, code, redirect_uri, state)
            
            # 2단계: 사용자 정보 조회
            user_info = await OAuthClient._fetch_profile(client, provider, token)
            
            return user_info

    @staticmethod
    async def _fetch_token(client: httpx.AsyncClient, provider: str, code: str, redirect_uri: str, state: str = None) -> str:
        url = ""
        data = {}
        # [공통] 모든 OAuth 요청은 x-www-form-urlencoded 형식을 따름
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}

        if provider == "kakao":
            url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "code": code
            }
            # 카카오는 Client Secret이 선택사항
            if settings.KAKAO_CLIENT_SECRET and settings.KAKAO_CLIENT_SECRET.strip():
                data["client_secret"] = settings.KAKAO_CLIENT_SECRET

        elif provider == "naver":
            import secrets
            url = "https://nid.naver.com/oauth2.0/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": settings.NAVER_CLIENT_ID,
                "client_secret": settings.NAVER_CLIENT_SECRET, # 네이버는 필수
                "code": code,
                "state": state if state else secrets.token_urlsafe(16),
                "redirect_uri": redirect_uri # 네이버는 인증 시 사용한 redirect_uri와 일치해야 함 (필수)
            }
            
        elif provider == "google":
            url = "https://oauth2.googleapis.com/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET, # 구글도 필수
                "redirect_uri": redirect_uri,
                "code": code
            }

        # [디버깅] 실제 전송 데이터 확인 (성공 후에는 주석 처리 추천)
        # print(f"🚀 [{provider}] Token Request Data: {data}")

        try:
            resp = await client.post(url, data=data, headers=headers)
            
            # [에러 처리] 각 Provider별 상세 에러 메시지 확인
            if resp.status_code != 200:
                print(f"❌ [{provider}] Token Error Body: {resp.text}")
            
            resp.raise_for_status()
            
            # 응답 파싱
            response_json = resp.json()
            return response_json.get("access_token")
            
        except httpx.HTTPStatusError as e:
            error_msg = e.response.json().get('error_description') or e.response.json().get('error') or "토큰 발급 실패"
            print(f"Token Exchange HTTP Error: {e.response.text}")
            raise HTTPException(status_code=400, detail=f"{provider} 로그인 실패: {error_msg}")
            
        except Exception as e:
            print(f"Token Exchange Error ({provider}): {str(e)}")
            raise HTTPException(status_code=400, detail=f"{provider} 로그인 실패: 알 수 없는 시스템 오류")

    @staticmethod
    async def _fetch_profile(client: httpx.AsyncClient, provider: str, access_token: str) -> dict:
        url = ""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if provider == "kakao":
            url = "https://kapi.kakao.com/v2/user/me"
        elif provider == "naver":
            url = "https://openapi.naver.com/v1/nid/me"
        elif provider == "google":
            url = "https://www.googleapis.com/oauth2/v2/userinfo"
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            # [중요] Provider마다 주는 데이터 모양이 달라서 통일(Normalize)해줘야 함
            return OAuthClient._normalize(provider, data)
            
        except Exception as e:
            print(f"Profile Fetch Error ({provider}): {str(e)}")
            raise HTTPException(status_code=400, detail=f"{provider} 로그인 실패: 프로필 조회 오류")

    @staticmethod
    def _normalize(provider: str, data: dict) -> dict:
        """우리 서비스에서 쓰기 편하게 데이터 모양 통일"""
        if provider == "kakao":
            account = data.get("kakao_account", {})
            return {
                "social_id": str(data.get("id")),
                "email": account.get("email"),
                "nickname": account.get("profile", {}).get("nickname")
            }
        elif provider == "naver":
            res = data.get("response", {})
            return {
                "social_id": res.get("id"),
                "email": res.get("email"),
                "nickname": res.get("name")
            }
        elif provider == "google":
            return {
                "social_id": data.get("id"),
                "email": data.get("email"),
                "nickname": data.get("name")
            }
        return {}