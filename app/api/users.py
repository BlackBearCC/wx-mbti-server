"""
用户管理API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/profile")
async def get_user_profile():
    """获取用户信息"""
    return {"message": "获取用户信息API - 待实现"}


@router.put("/profile")
async def update_user_profile():
    """更新用户信息"""
    return {"message": "更新用户信息API - 待实现"}


@router.get("/stats")
async def get_user_stats():
    """获取用户统计"""
    return {"message": "获取用户统计API - 待实现"}


@router.get("/characters")
async def get_user_characters():
    """获取用户角色库"""
    return {"message": "获取用户角色库API - 待实现"}
