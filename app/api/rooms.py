"""
聊天室管理API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_rooms():
    """获取聊天室列表"""
    return {"message": "获取聊天室列表API - 待实现"}


@router.get("/{room_id}")
async def get_room_detail():
    """获取聊天室详情"""
    return {"message": "获取聊天室详情API - 待实现"}


@router.post("/{room_id}/join")
async def join_room():
    """加入聊天室"""
    return {"message": "加入聊天室API - 待实现"}
