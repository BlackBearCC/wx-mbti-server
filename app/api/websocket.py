"""
WebSocket API路由
"""
from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket聊天端点"""
    await websocket.accept()
    await websocket.send_text("WebSocket连接已建立 - 待完善实现")
    await websocket.close()
