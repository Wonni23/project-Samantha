"""Legacy 기억 관리 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.models.content import LifeLegacy

router = APIRouter()


@router.get("/legacies")
async def get_all_legacies(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """DB에 저장된 전체 Legacy 조회 (삭제되지 않은 것만)"""
    result = await db.exec(
        select(LifeLegacy)
        .where(LifeLegacy.user_id == user_id, LifeLegacy.importance >= 0)
        .order_by(LifeLegacy.importance.desc(), LifeLegacy.created_at.desc())
    )
    legacies = result.all()
    return [
        {
            "id": lg.id,
            "summary": lg.summary,
            "category": lg.category.value,
            "importance": lg.importance,
        }
        for lg in legacies
    ]


@router.delete("/legacy/{legacy_id}", status_code=200)
async def delete_legacy(
    legacy_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Legacy soft-delete (importance = -1)"""
    legacy = await db.get(LifeLegacy, legacy_id)

    if not legacy or legacy.user_id != user_id:
        raise HTTPException(status_code=404, detail="해당 기억을 찾을 수 없습니다.")

    legacy.importance = -1
    db.add(legacy)
    await db.commit()

    return {"status": "ok", "deleted_id": legacy_id}
