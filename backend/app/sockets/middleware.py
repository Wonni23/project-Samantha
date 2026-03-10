import logging
from app.core.security import verify_access_token
from app.core.db import async_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


async def socket_auth_middleware(environ, handler):
    """
    Socket.IO 인증 미들웨어.
    미들웨어 단계에서는 sid가 없으므로 직접 에러를 보내지 않고,
    인증 결과만 environ에 담아 connect 이벤트로 넘깁니다.

    DB 오류 등 일시적 장애 시에는 connect 핸들러에 기회를 넘깁니다
    (auth 파라미터 경로로 재시도 가능).
    """
    auth_header = environ.get('HTTP_AUTHORIZATION', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None

    # 1. 토큰이 없는 경우 (connect 핸들러에서 auth 파라미터로 처리하도록 넘김)
    if not token:
        return await handler(environ)

    user_id = verify_access_token(token)

    # 2. 토큰 검증 실패 → 연결 거부
    if not user_id:
        logger.warning("[Middleware] Invalid token in Authorization header")
        return False

    # 3. DB 조회
    try:
        async with async_session_factory() as db:
            user = await db.get(User, user_id)
            if user:
                environ['auth_user'] = user
                return await handler(environ)
    except Exception as e:
        # DB 일시 장애 시 connect 핸들러에 기회를 넘김 (auth 파라미터 경로)
        logger.error("[Middleware] DB lookup failed, deferring to connect handler: %s", e)
        return await handler(environ)

    # 4. 토큰은 유효하지만 유저가 DB에 없음 → 거부
    logger.warning("[Middleware] User %s not found in DB", user_id)
    return False
