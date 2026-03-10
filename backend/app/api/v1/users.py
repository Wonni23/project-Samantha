from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.user_context import UserContext
# app/schemas/user_schema.py에 UserRead 모델이 있다고 가정합니다.
from app.schemas.user_schema import UserRead

router = APIRouter()

@router.get("/me", response_model=UserRead)
async def get_my_info(
    current_user: User = Depends(deps.get_current_user)
):
    """
    현재 로그인한 유저 정보를 반환합니다.
    이 엔드포인트는 deps.get_current_user를 통해 DB 조회를 강제하므로,
    DB가 삭제된 경우 401/404 에러를 반환하여 프론트엔드가 로그아웃 되도록 유도합니다.
    """
    return current_user


@router.get("/context")
async def get_user_context(
    user_id: int = Depends(deps.get_current_user_id),
    db: AsyncSession = Depends(deps.get_db),
):
    """DB에서 UserContext를 조회하여 5축 페르소나 + 전체 프로필을 반환합니다."""
    result = await db.exec(select(UserContext).where(UserContext.user_id == user_id))
    user_context = result.first()
    if not user_context:
        raise HTTPException(status_code=404, detail="UserContext not found")
    return {
        "persona_state": {
            "axis_playful": user_context.axis_playful,
            "axis_feisty": user_context.axis_feisty,
            "axis_dependent": user_context.axis_dependent,
            "axis_caregive": user_context.axis_caregive,
            "axis_reflective": user_context.axis_reflective,
        },
        "user_profile": user_context.user_profile or {},
        "user_title": user_context.user_title,
    }
