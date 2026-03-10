import logging
from datetime import datetime
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from app.sockets.manager import socket_manager, sio, SocketErrors
from app.core.security import verify_access_token
from app.core.exceptions import TTSException, STTException
from app.integrations.voice.base import TTSConfig
from app.services.storage_service import s3_uploader
from app.core.config import settings
from app.core.db import async_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


# TTS 동시 요청 제한 (사용자별 + 전체 상한)
_TTS_PER_USER_LIMIT = 3
_TTS_GLOBAL_LIMIT = 10
_TTS_GLOBAL_SEMAPHORE = asyncio.Semaphore(_TTS_GLOBAL_LIMIT)
_user_tts_semaphores: Dict[int, asyncio.Semaphore] = {}


def _get_user_semaphore(user_id: int) -> asyncio.Semaphore:
    """사용자별 TTS 세마포어를 반환 (없으면 생성)."""
    semaphore = _user_tts_semaphores.get(user_id)
    if semaphore is None:
        semaphore = asyncio.Semaphore(_TTS_PER_USER_LIMIT)
        _user_tts_semaphores[user_id] = semaphore
    return semaphore


def _cleanup_user_tts_semaphores(active_user_ids: List[int]) -> None:
    """현재 활성 유저 외 세마포어 엔트리를 정리."""
    active_user_set = set(active_user_ids)
    stale_user_ids = [
        user_id for user_id in list(_user_tts_semaphores.keys())
        if user_id not in active_user_set
    ]
    for user_id in stale_user_ids:
        _user_tts_semaphores.pop(user_id, None)


def _build_audio_chunk_payload(
    chunk: bytes, segment_index: int, chunk_index: int
) -> Dict[str, Any]:
    """오디오 청크 payload 생성 (기존 data 필드 + 세그먼트 메타)."""
    return {
        "data": chunk,
        "segment_index": segment_index,
        "chunk_index": chunk_index,
    }

def _build_tts_config(user_voice: Optional[str] = None) -> TTSConfig:
    """TTSConfig 생성. voice 우선순위: user_voice > settings default."""
    return TTSConfig(
        voice=user_voice or settings.TTS_DEFAULT_VOICE,
        speaking_rate=settings.TTS_DEFAULT_SPEED,
    )


async def _synth_with_semaphore(
    tts_svc: Any, user_id: int, text: str, tts_cfg: TTSConfig
) -> Optional[bytes]:
    """사용자별 + 전체 상한으로 제한된 TTS 합성."""
    user_semaphore = _get_user_semaphore(user_id)

    async with _TTS_GLOBAL_SEMAPHORE:
        async with user_semaphore:
            try:
                result = await tts_svc.synthesize(text, tts_cfg)
                return result.audio_content
            except TTSException as e:
                logger.warning("[TTS] 합성 실패: %s", e.message)
                return None


async def _stream_tts_to_client(
    sid: str,
    tts_svc: Any,
    user_id: int,
    text: str,
    tts_cfg: TTSConfig,
    segment_index: int,
) -> None:
    """첫 세그먼트 TTS 스트리밍 → 오디오 청크 즉시 emit."""
    user_semaphore = _get_user_semaphore(user_id)
    chunk_index = 0

    await sio.emit(
        "bot_audio_segment_start",
        {"segment_index": segment_index},
        room=sid,
    )

    async with _TTS_GLOBAL_SEMAPHORE:
        async with user_semaphore:
            try:
                async for chunk in tts_svc.synthesize_streaming(text, tts_cfg):
                    await sio.emit(
                        "bot_audio_chunk",
                        _build_audio_chunk_payload(chunk, segment_index, chunk_index),
                        room=sid,
                    )
                    chunk_index += 1
            except Exception as e:
                logger.warning("[TTS] Streaming failed, fallback to full: %s", e)
                try:
                    result = await tts_svc.synthesize(text, tts_cfg)
                    if result:
                        await sio.emit(
                            "bot_audio_chunk",
                            _build_audio_chunk_payload(
                                result.audio_content, segment_index, chunk_index
                            ),
                            room=sid,
                        )
                except TTSException as e2:
                    logger.warning("[TTS] Full synthesis also failed: %s", e2.message)

    await sio.emit(
        "bot_audio_segment_end",
        {"segment_index": segment_index},
        room=sid,
    )


async def _process_ai_stream(
    sid: str,
    ai_pipeline: Any,
    tts_service: Any,
    user_id: int,
    user_text: str,
    db: Any,
    user_voice: Optional[str] = None,
    prefetched_session: Any = None,
) -> None:
    """AI 파이프라인 스트림 처리 — audio_blob/text_message 공통 로직.

    이벤트 스트림을 순회하며 텍스트/감정/Live2D/TTS를 클라이언트에 emit.
    첫 세그먼트는 스트리밍, 후속 세그먼트는 병렬 합성 후 순서대로 emit.
    """
    tts_cfg = _build_tts_config(user_voice=user_voice)
    first_stream_task: Optional[asyncio.Task] = None
    subsequent_tts_tasks: List[Tuple[int, asyncio.Task]] = []
    next_segment_index = 0

    try:
        async for event in ai_pipeline.run_stream_with_voice(
            user_id, user_text, db,
            prefetched_session=prefetched_session,
        ):
            if event["type"] == "text":
                await sio.emit("bot_text_chunk", {"text": event["data"]}, room=sid)

            elif event["type"] == "tts_config":
                data = event["data"]
                emotion = data.get("emotion") or "serene"
                logger.debug(
                    "[TTS Config] voice=%s, speed=%s, emotion=%s",
                    tts_cfg.voice, tts_cfg.speaking_rate, emotion,
                )
                await sio.emit("bot_emotion", {"emotion": emotion}, room=sid)

            elif event["type"] == "live2d":
                raw_live2d = event.get("data") or {}
                live2d_payload: Dict[str, Any]
                if isinstance(raw_live2d, dict):
                    live2d_payload = dict(raw_live2d)
                else:
                    live2d_payload = {}

                expression = live2d_payload.get("expression")
                live2d_payload["expression"] = (
                    expression if isinstance(expression, str) else "serene"
                )

                intensity = live2d_payload.get("emotion_intensity")
                if isinstance(intensity, (int, float)):
                    live2d_payload["emotion_intensity"] = float(intensity)
                else:
                    # 프론트 파서의 num 강제 캐스팅 오류 방지
                    live2d_payload["emotion_intensity"] = 1.0

                await sio.emit("bot_live2d", live2d_payload, room=sid)

            elif event["type"] == "tts":
                segment_index = next_segment_index
                next_segment_index += 1
                if first_stream_task is None and tts_service.supports_streaming:
                    # 첫 세그먼트: 스트리밍으로 즉시 오디오 전송 시작
                    first_stream_task = asyncio.create_task(
                        _stream_tts_to_client(
                            sid,
                            tts_service,
                            user_id,
                            event["data"],
                            tts_cfg,
                            segment_index,
                        )
                    )
                else:
                    # 후속 세그먼트: 병렬 전체 합성 (나중에 순서대로 emit)
                    task = asyncio.create_task(
                        _synth_with_semaphore(
                            tts_service, user_id, event["data"], tts_cfg
                        )
                    )
                    subsequent_tts_tasks.append((segment_index, task))

            elif event["type"] == "rag_results":
                await sio.emit("bot_rag_results", event["data"], room=sid)

            elif event["type"] == "debug_info":
                await sio.emit("bot_debug_info", event["data"], room=sid)

            elif event["type"] == "done":
                # 1. 첫 세그먼트 스트리밍 완료 대기 (이미 emit 중/완료)
                if first_stream_task:
                    await first_stream_task

                # 2. 후속 세그먼트 순서대로 emit
                for segment_index, task in subsequent_tts_tasks:
                    try:
                        audio_chunk = await task
                        if audio_chunk:
                            await sio.emit(
                                "bot_audio_segment_start",
                                {"segment_index": segment_index},
                                room=sid,
                            )
                            await sio.emit(
                                "bot_audio_chunk",
                                _build_audio_chunk_payload(audio_chunk, segment_index, 0),
                                room=sid,
                            )
                            await sio.emit(
                                "bot_audio_segment_end",
                                {"segment_index": segment_index},
                                room=sid,
                            )
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.warning("[TTS] Segment failed: %s", e)
                        await socket_manager.send_error(
                            sid, "TTS_ERROR", "음성 변환에 실패했습니다. 텍스트로 확인해주세요.",
                        )

                await sio.emit("bot_response_done", {}, room=sid)
    except Exception:
        # pending TTS 태스크 정리
        if first_stream_task and not first_stream_task.done():
            first_stream_task.cancel()
        for _, task in subsequent_tts_tasks:
            if not task.done():
                task.cancel()
        raise


# 전역 상태 관리 변수
_ai_pipeline = None
_stt_service = None
_tts_service = None
IS_AI_READY = False

def init_ai_resources():
    global _ai_pipeline, _stt_service, _tts_service, IS_AI_READY
    if IS_AI_READY:
        return
    try:
        from app.engine.pipeline import SamanthaPipeline
        from app.services.stt_service import stt_service
        from app.integrations.voice import get_tts_provider

        _ai_pipeline = SamanthaPipeline()
        _stt_service = stt_service
        _tts_service = get_tts_provider()
        IS_AI_READY = True
        logger.info("[AI] Resources pre-loaded successfully.")
    except Exception as e:
        logger.error("[AI Resource Error] Failed to load modules: %s", e, exc_info=True)
        IS_AI_READY = False

def get_ai_resources():
    if not IS_AI_READY:
        init_ai_resources()
    return _ai_pipeline, _stt_service, _tts_service

# [개선] 코파일럿 지적 반영: 모듈 로드 시 실패해도 앱이 죽지 않도록 예외 처리
try:
    init_ai_resources()
except Exception as e:
    logger.warning("[AI] Resource initialization failed during import: %s", e)

async def _prepare_pipeline(user_id: int, pipeline) -> Optional[Any]:
    """STT 대기 중 파이프라인 준비 (session load + Actor cache ensure).

    Returns:
        SessionData if successful, None on failure (pipeline fallback).
    """
    try:
        async with async_session_factory() as prep_db:
            session = await pipeline._conversation_pipeline.init_session(prep_db, user_id)

        # Actor의 Context Cache가 아직 없으면 lazy init 트리거
        if hasattr(pipeline, 'expanded_actor') and pipeline.expanded_actor.use_cache:
            await pipeline.expanded_actor._ensure_cache()

        return session
    except Exception as e:
        logger.debug("[Prefetch] Pipeline prep failed (will fallback): %s", e)
        return None


async def _pre_warm_session(user_id: int) -> None:
    """연결 시 세션 사전 로드 → MemorySessionStore 캐싱.

    실패해도 audio_blob에서 정상 경로로 fallback하므로 무해.
    """
    try:
        ai_pipeline, _, _ = get_ai_resources()
        if ai_pipeline and IS_AI_READY:
            async with async_session_factory() as db:
                await ai_pipeline._conversation_pipeline.init_session(db, user_id)
            logger.debug("[Prefetch] Session pre-warmed: user_id=%s", user_id)
    except Exception as e:
        logger.debug("[Prefetch] Session pre-warm failed (will retry on audio_blob): %s", e)


@sio.event
async def connect(sid, environ, auth=None):
    logger.info("[Connect] Request from SID: %s", sid)

    # 1. 미들웨어에서 이미 인증된 경우 (HTTP_AUTHORIZATION 헤더 경로)
    user = environ.get('auth_user')

    # 2. 미들웨어를 거치지 않은 경우 → auth 파라미터로 직접 인증
    if not user:
        if not auth or 'token' not in auth:
            logger.warning("[Auth] No token provided for SID: %s", sid)
            return False

        user_id = verify_access_token(auth['token'])
        if user_id is None:
            logger.warning("[Auth] Invalid token for SID: %s", sid)
            return False

        try:
            async with async_session_factory() as db:
                user = await db.get(User, user_id)
        except Exception as e:
            logger.error("[Auth] DB lookup failed for SID %s: %s", sid, e)
            return False

    if not user:
        await socket_manager.send_error(sid, SocketErrors.AUTH_FAILED, "인증에 실패했습니다.")
        return False

    logger.info("[Auth] User %s authenticated (SID: %s)", user.id, sid)
    await socket_manager.register_session(sid, user.id)

    # Session pre-init (fire-and-forget): audio_blob 전에 캐시 warm-up
    asyncio.create_task(_pre_warm_session(user.id))

    await sio.emit('connection_ack', {'status': 'connected', 'msg': '시아가 듣고 있어요.'}, room=sid)

@sio.event
async def disconnect(sid):
    logger.info("[Disconnect] SID: %s", sid)
    # cleanup_session이 이제 비동기 함수이므로 await 필요
    await socket_manager.cleanup_session(sid)
    active_user_ids = await socket_manager.get_active_user_ids()
    _cleanup_user_tts_semaphores(active_user_ids)

@sio.event
async def audio_blob(sid, data):
    file_url = None
    try:
        await socket_manager.update_activity(sid)

        MAX_AUDIO_SIZE = 10 * 1024 * 1024
        # 오디오 데이터 유효성 검증: 빈 데이터 및 타입 체크
        if not data:
            await socket_manager.send_error(sid, "INVALID_AUDIO_DATA", "오디오 데이터가 비어있습니다")
            return
        if not isinstance(data, bytes):
            await socket_manager.send_error(sid, "INVALID_AUDIO_DATA", "유효하지 않은 오디오 데이터 형식입니다")
            return
        if len(data) > MAX_AUDIO_SIZE:
            await socket_manager.send_error(sid, "LIMIT_EXCEEDED", "전송된 오디오 데이터가 너무 큽니다.")
            return

        logger.info("[Audio] Received %d bytes from SID: %s", len(data), sid)

        file_url = await s3_uploader.upload_bytes(
            data,
            folder="voice_inputs",
            filename=f"{sid}_{datetime.now().timestamp()}.webm"
        )
        await sio.emit('audio_ack', {'status': 'uploaded', 'url': file_url}, room=sid)

        ai_pipeline, stt_service, tts_service = get_ai_resources()

        if IS_AI_READY:
            user_id = await socket_manager.get_user_id(sid)
            if not user_id:
                raise ValueError("인증 정보를 찾을 수 없습니다.")

            async with async_session_factory() as db:
                # STT + 파이프라인 준비를 병렬 실행
                stt_task = asyncio.create_task(stt_service.transcribe(data))
                prep_task = asyncio.create_task(
                    _prepare_pipeline(user_id, ai_pipeline)
                )

                # STT 결과 + 할루시네이션 검사
                try:
                    result = await stt_task
                except Exception:
                    prep_task.cancel()
                    try:
                        await prep_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    raise

                if not result.text or not result.text.strip() or result.is_hallucination:
                    prep_task.cancel()
                    try:
                        await prep_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    if file_url:
                        await s3_uploader.delete_file(file_url)
                    await socket_manager.send_error(
                        sid, "STT_ERROR",
                        "사용자님, 목소리가 잘 들리지 않아서요. 다시 말씀해주시겠어요?"
                    )
                    return

                user_text = result.text

                # STT 변환 텍스트를 프론트엔드로 전송
                await sio.emit('stt_text', {'text': user_text}, room=sid)

                # Pipeline prep 결과 수집 (실패 시 None → pipeline fallback)
                prefetched_session = await prep_task

                # 사용자별 TTS voice 조회 (user_profile에 저장된 경우)
                # TODO: user.tts_voice 필드 추가 시 여기서 가져오기
                user_voice: Optional[str] = None

                await _process_ai_stream(
                    sid, ai_pipeline, tts_service,
                    user_id, user_text, db,
                    user_voice=user_voice,
                    prefetched_session=prefetched_session,
                )
        else:
            await socket_manager.send_error(sid, SocketErrors.INTERNAL_ERROR, "시스템 준비 중입니다. 잠시 후 다시 시도해주세요.")

    except STTException as e:
        logger.warning("[STT] 음성 인식 실패: %s", e.message)
        if file_url:
            success = await s3_uploader.delete_file(file_url)
            if not success:
                logger.warning("[Storage] Orphan file after STT failure: %s", file_url)
        await socket_manager.send_error(sid, "STT_ERROR", "음성 인식에 실패했습니다. 다시 말씀해주시겠어요?")
        return

    except Exception as e:
        # [개선] 보안: 상세 에러(str(e))는 로그에만, 사용자에겐 일반 메시지
        log_msg = f"대화 처리 중 오류: [{type(e).__name__}] {str(e)}"
        user_msg = "대화 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        logger.error(log_msg, exc_info=True)

        if file_url:
            success = await s3_uploader.delete_file(file_url)
            if not success:
                logger.critical("[Storage] Orphan file remains: %s", file_url)

        await socket_manager.send_error(sid, SocketErrors.INTERNAL_ERROR, user_msg)

@sio.event
async def text_message(sid, data):
    """텍스트 메시지 처리 — STT/S3 없이 파이프라인 직접 실행"""
    try:
        await socket_manager.update_activity(sid)

        if not data or not isinstance(data, dict):
            await socket_manager.send_error(sid, "INVALID_DATA", "유효하지 않은 데이터입니다")
            return

        user_text = (data.get("text") or "").strip()
        if not user_text:
            await socket_manager.send_error(sid, "EMPTY_TEXT", "메시지가 비어있습니다")
            return

        if len(user_text) > 2000:
            await socket_manager.send_error(sid, "LIMIT_EXCEEDED", "메시지가 너무 깁니다.")
            return

        logger.info("[Text] Received %d chars from SID: %s", len(user_text), sid)

        ai_pipeline, _, tts_service = get_ai_resources()

        if IS_AI_READY:
            user_id = await socket_manager.get_user_id(sid)
            if not user_id:
                raise ValueError("인증 정보를 찾을 수 없습니다.")

            async with async_session_factory() as db:
                await _process_ai_stream(
                    sid, ai_pipeline, tts_service,
                    user_id, user_text, db,
                )
        else:
            await socket_manager.send_error(sid, SocketErrors.INTERNAL_ERROR, "시스템 준비 중입니다. 잠시 후 다시 시도해주세요.")

    except Exception as e:
        log_msg = f"텍스트 처리 중 오류: [{type(e).__name__}] {str(e)}"
        user_msg = "대화 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        logger.error(log_msg, exc_info=True)
        await socket_manager.send_error(sid, SocketErrors.INTERNAL_ERROR, user_msg)

@sio.event
async def ping_response(sid, data):
    await socket_manager.update_activity(sid)
