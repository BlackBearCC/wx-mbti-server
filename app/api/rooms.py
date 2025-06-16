"""
聊天室管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException # Added Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict # Added Dict
import time # Added time for mock data

router = APIRouter()

# Placeholder for JWT token dependency (copied from other api modules for consistency)
async def get_current_user_placeholder(token: Optional[str] = Depends(lambda x: x.headers.get("Authorization"))):
    if not token or not token.startswith("Bearer "):
        # For listing rooms, we might allow unauthenticated access, so this check could be optional
        # or handled differently based on whether authentication is strictly required for this endpoint.
        # For now, let's assume it's not strictly required for GET /rooms, but keep the dependency for potential future use.
        # If token is present, validate it.
        try:
            user_id = token.split("_")[-1]
            return {"userId": user_id, "userLevel": "normal"}
        except IndexError:
            # If token is present but invalid, then it's an issue.
            raise HTTPException(status_code=401, detail="Invalid token format for mock")
    return None # No token, or not strictly required for this endpoint

# --- Mock Room Data Store ---
mock_rooms_db = {
    "room_tech_talk_001": {
        "roomId": "room_tech_talk_001",
        "name": "科技前沿讨论室",
        "description": "讨论最新的科技趋势、AI进展、未来技术等。",
        "coverImage": "/static/rooms/tech_cover.jpg",
        "characterId": "intj_scientist_001", # 主持人/核心角色ID
        "characterName": "艾米·科学家",
        "characterAvatar": "/static/characters/intj_scientist.svg",
        "tags": ["科技", "AI", "创新"],
        "memberCount": 125,
        "lastActiveTime": time.time() - (2 * 60 * 60), # 2 hours ago
        "isHot": True,
        "isNew": False,
        "createTime": time.time() - (10 * 24 * 60 * 60) # 10 days ago
    },
    "room_art_corner_002": {
        "roomId": "room_art_corner_002",
        "name": "文艺创作角落",
        "description": "分享诗歌、绘画、音乐等艺术创作和感悟。",
        "coverImage": "/static/rooms/art_cover.jpg",
        "characterId": "infp_dreamer_002",
        "characterName": "露娜·梦想家",
        "characterAvatar": "/static/characters/infp_dreamer.svg",
        "tags": ["艺术", "创作", "文学"],
        "memberCount": 78,
        "lastActiveTime": time.time() - (5 * 60 * 60), # 5 hours ago
        "isHot": False,
        "isNew": True, # Assuming created recently
        "createTime": time.time() - (2 * 24 * 60 * 60) # 2 days ago
    }
}

# --- Pydantic Models for Room Listing ---
class RoomPreview(BaseModel):
    roomId: str
    name: str
    description: str
    coverImage: str
    characterId: str
    characterName: str
    characterAvatar: str
    tags: List[str]
    memberCount: int
    lastActiveTime: float
    isHot: bool = False
    isNew: bool = False

class GetRoomsResponseData(BaseModel):
    rooms: List[RoomPreview]
    # Potentially add pagination or filter metadata here in the future

class GetRoomsResponse(BaseModel):
    code: int = 200
    data: GetRoomsResponseData

# --- Pydantic Models for Room Detail ---
class RoomMessage(BaseModel):
    messageId: str
    userId: str
    username: str
    avatar: str
    characterId: Optional[str] = None # If message is from a character
    characterName: Optional[str] = None
    content: str
    messageType: str # e.g., "text", "image", "system"
    timestamp: float
    reactions: Optional[Dict[str, int]] = None # e.g., {"like": 10, "love": 2}

class RoomMember(BaseModel):
    userId: str
    username: str
    avatar: str
    isOnline: bool
    lastSeen: Optional[float] = None

class RoomCharacterInfo(BaseModel): # Info about the main character of the room
    characterId: str
    name: str
    avatar: str
    dimension: str
    background: str
    # Could add more character details if needed for the room view

class GetRoomDetailResponseData(BaseModel):
    roomId: str
    name: str
    description: str
    coverImage: str
    characterInfo: RoomCharacterInfo
    tags: List[str]
    memberCount: int
    onlineMemberCount: int
    members: List[RoomMember] # Paginated or limited list
    messages: List[RoomMessage] # Paginated or limited list, newest first
    userRole: str # e.g., "member", "admin", "owner"
    # lastReadMessageId: Optional[str] = None # For user to track unread messages

class GetRoomDetailResponse(BaseModel):
    code: int = 200
    data: GetRoomDetailResponseData

# --- Pydantic Models for Join Room Endpoint ---
class JoinRoomResponseData(BaseModel):
    roomId: str
    status: str # e.g., "success", "already_joined", "room_full", "not_found"
    message: Optional[str] = None
    # newMemberCount: Optional[int] = None

class JoinRoomResponse(BaseModel):
    code: int = 200
    data: JoinRoomResponseData

# Mock user-room membership (very simplified)
# In a real app, this would be a proper database table
mock_user_room_memberships = {
    "user_123": ["room_tech_talk_001"] # User 123 is already in room_tech_talk_001
}

# Extended mock_rooms_db with more details for get_room_detail
mock_room_details_db = {
    "room_tech_talk_001": {
        # Basic info from mock_rooms_db
        "roomId": "room_tech_talk_001",
        "name": "科技前沿讨论室",
        "description": "讨论最新的科技趋势、AI进展、未来技术等。",
        "coverImage": "/static/rooms/tech_cover.jpg",
        "characterId": "intj_scientist_001",
        "characterName": "艾米·科学家",
        "characterAvatar": "/static/characters/intj_scientist.svg",
        "tags": ["科技", "AI", "创新"],
        "memberCount": 125,
        # Detailed info for this endpoint
        "characterInfo": {
            "characterId": "intj_scientist_001", "name": "艾米·科学家", "avatar": "/static/characters/intj_scientist.svg",
            "dimension": "INTJ", "background": "科学家"
        },
        "onlineMemberCount": 30,
        "members": [
            {"userId": "user_123", "username": "Alice", "avatar": "/static/avatars/alice.png", "isOnline": True},
            {"userId": "user_456", "username": "Bob", "avatar": "/static/avatars/bob.png", "isOnline": False, "lastSeen": time.time() - 3600},
        ],
        "messages": [
            {
                "messageId": "msg_002", "userId": "intj_scientist_001", "username": "艾米·科学家", "avatar": "/static/characters/intj_scientist.svg",
                "characterId": "intj_scientist_001", "characterName": "艾米·科学家",
                "content": "欢迎来到科技前沿讨论室！今天我们来聊聊量子计算的最新突破。", "messageType": "text", "timestamp": time.time() - 600
            },
            {
                "messageId": "msg_001", "userId": "user_123", "username": "Alice", "avatar": "/static/avatars/alice.png",
                "content": "我对量子计算很感兴趣！", "messageType": "text", "timestamp": time.time() - 500, "reactions": {"like": 5}
            }
        ],
        "userRole": "member" # Mock role for the current user
    }
    # Add details for other rooms as needed
}

@router.get("/{room_id}", response_model=GetRoomDetailResponse)
async def get_room_detail(room_id: str, current_user: Optional[dict] = Depends(get_current_user_placeholder)):
    """获取聊天室详情"""
    room_detail_data = mock_room_details_db.get(room_id)
    if not room_detail_data:
        # Fallback to basic info if detail not found, but ideally all rooms should have details
        basic_room_data = mock_rooms_db.get(room_id)
        if not basic_room_data:
            raise HTTPException(status_code=404, detail="Room not found")
        # Construct a minimal detail response from basic data (this part might need more fleshing out)
        # For now, let's assume if it's not in mock_room_details_db, it's an error or needs to be created.
        # This simplified fallback might not satisfy all fields of GetRoomDetailResponseData.
        # It's better to ensure mock_room_details_db is comprehensive.
        raise HTTPException(status_code=404, detail="Room details not found, and basic data is insufficient.")

    # Simulate fetching character details if not fully embedded (already embedded in this mock)
    # char_info = mock_characters_db.get(room_detail_data["characterId"]) # Assuming mock_characters_db is accessible
    # if not char_info:
    #     raise HTTPException(status_code=500, detail="Room's main character data not found")
    # room_detail_data["characterInfo"] = RoomCharacterInfo(
    #     characterId=char_info["characterId"],
    #     name=char_info["name"],
    #     avatar=char_info["avatar"],
    #     dimension=char_info["dimension"],
    #     background=char_info["background"]
    # )

    # Mock user role - in a real app, this would depend on the current_user and room membership
    user_specific_role = "member"
    if current_user and current_user.get("userId") == "admin_user_id_placeholder": # Example admin
        user_specific_role = "admin"
    
    # Ensure all fields are present for the response model
    # The mock_room_details_db should be structured to directly map to GetRoomDetailResponseData
    final_response_data = GetRoomDetailResponseData(**room_detail_data, userRole=user_specific_role)

    return GetRoomDetailResponse(data=final_response_data)


@router.post("/{room_id}/join", response_model=JoinRoomResponse)
async def join_room(room_id: str, current_user: dict = Depends(get_current_user_placeholder)):
    """加入聊天室"""
    if not current_user or not current_user.get("userId"):
        raise HTTPException(status_code=401, detail="Authentication required to join a room.")
    
    user_id = f"user_{current_user['userId']}"

    # Check if room exists
    if room_id not in mock_rooms_db and room_id not in mock_room_details_db:
        # A more robust check would be against a single source of truth for rooms
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found.")

    # Initialize user's memberships if not present
    if user_id not in mock_user_room_memberships:
        mock_user_room_memberships[user_id] = []

    # Check if already a member
    if room_id in mock_user_room_memberships[user_id]:
        return JoinRoomResponse(data=JoinRoomResponseData(
            roomId=room_id,
            status="already_joined",
            message="You are already a member of this room."
        ))

    # Mock joining logic
    mock_user_room_memberships[user_id].append(room_id)
    
    # Optionally, update member count in mock_rooms_db (if it's meant to be dynamic)
    if room_id in mock_rooms_db:
        mock_rooms_db[room_id]["memberCount"] = mock_rooms_db[room_id].get("memberCount", 0) + 1
    elif room_id in mock_room_details_db: # Also check details db if it's the source
         mock_room_details_db[room_id]["memberCount"] = mock_room_details_db[room_id].get("memberCount", 0) + 1

    return JoinRoomResponse(data=JoinRoomResponseData(
        roomId=room_id,
        status="success",
        message="Successfully joined the room.",
        # newMemberCount=mock_rooms_db.get(room_id, {}).get("memberCount") # Example
    ))
