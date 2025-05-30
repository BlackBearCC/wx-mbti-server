"""
角色管理API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_characters():
    """获取角色列表"""
    return {"message": "获取角色列表API - 待实现"}


@router.get("/{character_id}")
async def get_character_detail():
    """获取角色详情"""
    return {"message": "获取角色详情API - 待实现"}


@router.post("/unlock")
async def unlock_character():
    """解锁角色"""
    return {"message": "解锁角色API - 待实现"} 