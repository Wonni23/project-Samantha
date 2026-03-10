import socketio
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI
from app.core.config import settings

logger = logging.getLogger(__name__)


class SocketErrors:
    IDLE_TIMEOUT = "IDLE_TIMEOUT"
    DUPLICATE_LOGIN = "DUPLICATE_LOGIN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    AUTH_FAILED = "AUTH_FAILED"


class SocketManager:
    def __init__(self):
        self.server = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins=settings.CORS_ORIGINS,
            ping_interval=settings.SOCKET_PING_INTERVAL,
            ping_timeout=settings.SOCKET_PING_TIMEOUT,
            max_http_buffer_size=10 * 1024 * 1024,
            logger=True, 
            engineio_logger=True
        )
        self.app = socketio.ASGIApp(self.server, socketio_path="")
        self._active_sockets: Dict[str, datetime] = {}
        self._sid_to_user: Dict[str, int] = {}
        self._user_to_sid: Dict[int, str] = {}
        self._lock = asyncio.Lock()
        self._is_running = False
        self._idle_task: asyncio.Task | None = None

    def mount_to_app(self, app: FastAPI, path: str = "/ws/socket.io"):
        app.mount(path, self.app)

    async def start_background_task(self):
        self._is_running = True
        self._idle_task = asyncio.create_task(self._background_idle_check())

    async def stop_background_task(self):
        self._is_running = False
        if self._idle_task:
            self._idle_task.cancel()
            try:
                await self._idle_task
            except asyncio.CancelledError:
                pass
            self._idle_task = None

    async def register_session(self, sid: str, user_id: int):
        old_sid = None
        async with self._lock:
            if user_id in self._user_to_sid:
                old_sid = self._user_to_sid[user_id]
                if old_sid != sid:
                    # [데드락 방지] 락 내부에서 기존 세션 데이터를 먼저 정리
                    self._active_sockets.pop(old_sid, None)
                    self._sid_to_user.pop(old_sid, None)
                else:
                    old_sid = None  # 같은 SID면 disconnect 불필요

            self._active_sockets[sid] = datetime.now()
            self._sid_to_user[sid] = user_id
            self._user_to_sid[user_id] = sid
            logger.info("Session registered: user_id=%s, sid=%s", user_id, sid)

        # [데드락 방지] 락 해제 후 소켓 연결 종료 수행
        if old_sid:
            try:
                await self.send_error(old_sid, SocketErrors.DUPLICATE_LOGIN, "다른 기기에서 접속하여 연결을 종료합니다.")
                await self.server.disconnect(old_sid)
            except Exception as e:
                logger.warning("Failed to disconnect old session: old_sid=%s, error=%s", old_sid, e)

    async def cleanup_session(self, sid: str):
        """세션 삭제 시 락을 사용하여 보호합니다."""
        async with self._lock:
            self._active_sockets.pop(sid, None)
            user_id = self._sid_to_user.pop(sid, None)
            if user_id and self._user_to_sid.get(user_id) == sid:
                self._user_to_sid.pop(user_id, None)

    async def update_activity(self, sid: str):
        async with self._lock:
            if sid in self._active_sockets:
                self._active_sockets[sid] = datetime.now()

    async def get_user_id(self, sid: str):
        async with self._lock:
            return self._sid_to_user.get(sid)

    async def get_active_user_ids(self) -> List[int]:
        async with self._lock:
            return list(self._user_to_sid.keys())

    async def send_error(self, sid: str, code: str, msg: str):
        try:
            await self.server.emit('error', {'code': code, 'msg': msg}, room=sid)
        except Exception as e:
            logger.error("Failed to send error message: sid=%s, code=%s, error=%s", sid, code, e)

    async def _background_idle_check(self):
        """[N-03] Idle Connection Monitor (데드락 방지 버전)"""
        logger.info("Idle monitor started: timeout=%s minutes", settings.SOCKET_IDLE_TIMEOUT_MINUTES)
        timeout_delta = timedelta(minutes=settings.SOCKET_IDLE_TIMEOUT_MINUTES)
        
        while self._is_running:
            await asyncio.sleep(settings.SOCKET_IDLE_CHECK_INTERVAL)
            now = datetime.now()
            expired_sids: List[str] = []
            
            # 1. 락을 잡고 타임아웃 대상 식별 및 세션 데이터 즉시 정리
            async with self._lock:
                for sid, last_active in list(self._active_sockets.items()):
                    if now - last_active > timeout_delta:
                        expired_sids.append(sid)
                        # [데드락 방지] disconnect 호출 전 락 내부에서 데이터를 먼저 정리
                        self._active_sockets.pop(sid, None)
                        user_id = self._sid_to_user.pop(sid, None)
                        if user_id and self._user_to_sid.get(user_id) == sid:
                            self._user_to_sid.pop(user_id, None)

            # 2. 락을 해제한 상태에서 소켓 연결 종료 수행
            for sid in expired_sids:
                logger.info("Auto-disconnect idle connection: sid=%s", sid)
                try:
                    await self.send_error(sid, SocketErrors.IDLE_TIMEOUT, "오랫동안 활동이 없어 연결이 종료되었습니다.")
                    await self.server.disconnect(sid)
                except Exception as e:
                    logger.warning("Failed to disconnect idle session: sid=%s, error=%s", sid, e)


socket_manager = SocketManager()
sio = socket_manager.server
