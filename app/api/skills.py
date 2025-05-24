"""
技能系统API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/progress/{character_id}")
async def get_skill_progress():
    """获取技能进度"""
    return {"message": "获取技能进度API - 待实现"}


@router.post("/upgrade")
async def upgrade_skill():
    """技能升级"""
    return {"message": "技能升级API - 待实现"}
