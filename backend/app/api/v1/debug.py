"""디버그 전용 API — 데이터 초기화"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.core.config import settings
from app.models.content import Conversation, LifeLegacy
from app.models.user_context import UserContext

router = APIRouter()


def _ensure_debug_route_enabled() -> None:
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/reset")
async def reset_user_data(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    유저의 모든 AI 관련 데이터를 초기 상태로 리셋합니다.

    초기화 대상:
    - UserContext: 5축, 프로필, 요약, 퀘스트 → 기본값
    - LifeLegacy: 전체 hard-delete
    - Conversation: 전체 hard-delete
    - 인메모리 세션 캐시 삭제
    """
    _ensure_debug_route_enabled()
    counts = {}

    # 1. UserContext 초기화
    result = await db.exec(select(UserContext).where(UserContext.user_id == user_id))
    ctx = result.first()
    if ctx:
        ctx.axis_playful = 0.5
        ctx.axis_feisty = 0.2
        ctx.axis_dependent = 0.2
        ctx.axis_caregive = 0.5
        ctx.axis_reflective = 0.1
        ctx.user_profile = {}
        ctx.last_summary = {}
        ctx.legacy_progress = {}
        ctx.user_title = "선생님"
        db.add(ctx)
        counts["user_context"] = "reset"

    # 2. LifeLegacy 전체 삭제
    legacy_result = await db.execute(
        delete(LifeLegacy).where(LifeLegacy.user_id == user_id)
    )
    counts["legacies_deleted"] = legacy_result.rowcount

    # 3. Conversation 전체 삭제
    conv_result = await db.execute(
        delete(Conversation).where(Conversation.user_id == user_id)
    )
    counts["conversations_deleted"] = conv_result.rowcount

    await db.commit()

    # 4. 인메모리 세션 캐시 삭제
    try:
        from app.sockets.events import get_ai_resources
        ai_pipeline, _, _ = get_ai_resources()
        if ai_pipeline:
            await ai_pipeline._conversation_pipeline.store.delete(user_id)
            counts["session_cache"] = "cleared"
    except Exception:
        counts["session_cache"] = "skipped"

    return {"status": "ok", "reset": counts}
