# app/middleware/security.py

import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP 요청을 HTTPS로 강제 리디렉션하는 미들웨어"""
    
    def __init__(self, app: ASGIApp, force_https: bool = True):
        super().__init__(app)
        self.force_https = force_https
    
    async def dispatch(self, request: Request, call_next):
        # 개발 환경에서는 HTTPS 강제를 비활성화할 수 있음
        if not self.force_https:
            response = await call_next(request)
            return response
        
        # 헬스체크는 HTTP 허용
        if request.url.path == "/health":
            response = await call_next(request)
            return response
        
        # X-Forwarded-Proto 헤더 확인 (프록시/로드밸런서 환경)
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto and forwarded_proto.lower() == "https":
            response = await call_next(request)
            return response
        
        # 직접 HTTPS 연결 확인
        if request.url.scheme == "https":
            response = await call_next(request)
            return response
        
        # HTTP 요청인 경우 HTTPS로 리디렉션
        https_url = request.url.replace(scheme="https")
        logger.info(f"HTTP 요청을 HTTPS로 리디렉션: {request.url} -> {https_url}")
        return RedirectResponse(url=str(https_url), status_code=status.HTTP_301_MOVED_PERMANENTLY)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더를 추가하는 미들웨어"""
    
    def __init__(self, app: ASGIApp, force_https: bool = True):
        super().__init__(app)
        # force_https가 True인 환경(주로 프로덕션)에서만 HSTS를 적용
        self.force_https = force_https
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HSTS는 실제 HTTPS가 보장되는 환경에서만 설정
        if self.force_https:
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
            is_https = forwarded_proto == "https" or request.url.scheme == "https"
            if is_https:
                # localhost에서는 캐싱 꼬임 방지를 위해 HSTS 수명을 짧게(60초) 설정
                hostname = request.url.hostname
                if hostname in ("localhost", "127.0.0.1", "::1"):
                    response.headers["Strict-Transport-Security"] = "max-age=60; includeSubDomains"
                else:
                    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HTTPS에서만 쿠키 전송 - Set-Cookie 헤더를 안전하게 수정
        if hasattr(response, "raw_headers"):
            new_raw_headers = []
            for name, value in response.raw_headers:
                if name.lower() == b"set-cookie":
                    try:
                        cookie_str = value.decode("latin-1")
                    except Exception:
                        new_raw_headers.append((name, value))
                        continue

                    if "Secure" not in cookie_str:
                        cookie_str += "; Secure"
                    if "SameSite" not in cookie_str:
                        cookie_str += "; SameSite=Strict"

                    value = cookie_str.encode("latin-1")

                new_raw_headers.append((name, value))

            response.raw_headers = tuple(new_raw_headers)
        
        return response