"""
WebSocket连接管理器
"""
from typing import Dict, List, Set
from fastapi import WebSocket
import structlog
import json

logger = structlog.get_logger()


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接 {user_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储房间连接 {room_id: {user_id1, user_id2, ...}}
        self.room_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        
        logger.info("WebSocket连接建立", user_id=user_id)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开连接"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # 如果用户没有其他连接，则清理
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
                # 从所有房间中移除用户
                for room_id in self.room_connections:
                    self.room_connections[room_id].discard(user_id)
        
        logger.info("WebSocket连接断开", user_id=user_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """发送个人消息"""
        if user_id in self.active_connections:
            message_str = json.dumps(message, ensure_ascii=False)
            
            # 发送给用户的所有连接
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    logger.warning("发送个人消息失败", user_id=user_id, error=str(e))
                    disconnected.append(websocket)
            
            # 清理断开的连接
            for ws in disconnected:
                self.disconnect(ws, user_id)
    
    async def broadcast_to_room(self, message: dict, room_id: str, exclude_user: str = None):
        """向房间广播消息"""
        if room_id in self.room_connections:
            message_str = json.dumps(message, ensure_ascii=False)
            
            for user_id in self.room_connections[room_id]:
                if exclude_user and user_id == exclude_user:
                    continue
                
                await self.send_personal_message(message, user_id)
    
    def join_room(self, user_id: str, room_id: str):
        """加入房间"""
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        
        self.room_connections[room_id].add(user_id)
        logger.info("用户加入房间", user_id=user_id, room_id=room_id)
    
    def leave_room(self, user_id: str, room_id: str):
        """离开房间"""
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(user_id)
            
            # 如果房间为空，则删除房间
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        logger.info("用户离开房间", user_id=user_id, room_id=room_id)
    
    def get_room_users(self, room_id: str) -> Set[str]:
        """获取房间用户列表"""
        return self.room_connections.get(room_id, set())
    
    def get_user_rooms(self, user_id: str) -> List[str]:
        """获取用户所在的房间列表"""
        rooms = []
        for room_id, users in self.room_connections.items():
            if user_id in users:
                rooms.append(room_id)
        return rooms
    
    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
