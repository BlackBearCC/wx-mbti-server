"""
用户管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from app.utils.url import build_base_url
import time

router = APIRouter()

# Mock database or user service
fake_users_db = {}

# Placeholder for JWT token dependency
async def get_current_user(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    token = authorization
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    # In a real app, decode and validate token, then fetch user
    # For now, let's assume token is "Bearer mock_jwt_token_for_user_some_id"
    # and extract user_id from it.
    try:
        user_id_from_token = token.split("_")[-1]
        if user_id_from_token not in fake_users_db:
             # If user not in our mock_db from a previous login, create a mock one for profile get/put
            mock_user_for_profile = {
                "userId": user_id_from_token,
                "openid": f"mock_openid_for_{user_id_from_token}",
                "nickName": "Mock User",
                "avatarUrl": "http://example.com/avatar.png",
                "gender": 0,
                "country": "MockCountry",
                "province": "MockProvince",
                "city": "MockCity",
                "userLevel": "normal",
                "totalMessages": 0,
                "totalLikes": 0,
                "ownedCharacters": 0,
                "totalSkillLevel": 0,
                "joinedRooms": [],
                "favoriteCharacters": [],
                "createTime": time.time(),
                "lastLoginTime": time.time()
            }
            fake_users_db[user_id_from_token] = mock_user_for_profile
        return fake_users_db[user_id_from_token] # Return the user dict
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid token format")

class JoinedRoomInfo(BaseModel):
    roomId: str
    joinTime: float = Field(default_factory=time.time)
    lastActiveTime: float = Field(default_factory=time.time)

class FavoriteCharacterInfo(BaseModel):
    characterId: str
    name: str
    level: int
    totalSkillLevel: int

class UserProfileResponseData(BaseModel):
    userId: str
    openid: str
    nickName: str
    avatarUrl: str
    gender: int
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    userLevel: str
    totalMessages: int
    totalLikes: int
    ownedCharacters: int
    totalSkillLevel: int
    joinedRooms: List[JoinedRoomInfo]
    favoriteCharacters: List[FavoriteCharacterInfo]
    createTime: float
    lastLoginTime: float

class UserProfileResponse(BaseModel):
    code: int = 200
    data: UserProfileResponseData

class UpdateUserProfileRequest(BaseModel):
    nickName: Optional[str] = None
    avatarUrl: Optional[str] = None
    gender: Optional[int] = None

class UpdateUserProfileResponse(BaseModel):
    code: int = 200
    message: str = "更新成功"
    data: UserProfileResponseData # Reusing the same data model for updated user info

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """获取用户信息"""
    # current_user is already a dict from our mock get_current_user
    # In a real app, current_user might be a User model instance
    # We need to ensure all fields required by UserProfileResponseData are present
    # or provide defaults if they can be missing from the 'current_user' dict.
    
    # Example: ensure joinedRooms and favoriteCharacters are lists if not present
    current_user.setdefault("joinedRooms", [])
    current_user.setdefault("favoriteCharacters", [])
    current_user.setdefault("totalMessages", 0)
    current_user.setdefault("totalLikes", 0)
    current_user.setdefault("ownedCharacters", 0)
    current_user.setdefault("totalSkillLevel", 0)
    current_user.setdefault("userLevel", "normal")
    current_user.setdefault("gender", 0)

    # If current_user was from a DB model, you might convert it to Pydantic model here
    # For now, we assume current_user dict matches UserProfileResponseData structure
    # after ensuring default for lists.
    
    # Add user to fake_users_db if they logged in via wxlogin and it's their first profile access
    if current_user["userId"] not in fake_users_db:
        fake_users_db[current_user["userId"]] = current_user
        
    return UserProfileResponse(data=UserProfileResponseData(**current_user))

@router.put("/profile", response_model=UpdateUserProfileResponse)
async def update_user_profile(request_data: UpdateUserProfileRequest, current_user: dict = Depends(get_current_user)):
    """更新用户信息"""
    user_id = current_user["userId"]
    user_data = fake_users_db.get(user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = request_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            user_data[field] = value
    
    user_data["lastLoginTime"] = time.time() # Update last activity time on profile update
    fake_users_db[user_id] = user_data

    # Ensure all fields for response are present
    user_data.setdefault("joinedRooms", [])
    user_data.setdefault("favoriteCharacters", [])
    user_data.setdefault("totalMessages", 0)
    user_data.setdefault("totalLikes", 0)
    user_data.setdefault("ownedCharacters", 0)
    user_data.setdefault("totalSkillLevel", 0)
    user_data.setdefault("userLevel", "normal")
    user_data.setdefault("gender", 0)

    return UpdateUserProfileResponse(data=UserProfileResponseData(**user_data))


class UserStatistics(BaseModel):
    totalMessages: int
    totalLikes: int
    totalDays: int
    roomsCount: int
    favoriteAICount: int

class Achievement(BaseModel):
    achievementId: str
    name: str
    description: str
    unlockTime: float = Field(default_factory=time.time)

class WeeklyStats(BaseModel):
    messagesCount: int
    likesReceived: int
    likesGiven: int
    activeHours: float

class UserStatsResponseData(BaseModel):
    userId: str
    userLevel: str
    currentLevelExp: int
    nextLevelExp: int
    statistics: UserStatistics
    achievements: List[Achievement]
    weeklyStats: WeeklyStats

class UserStatsResponse(BaseModel):
    code: int = 200
    data: UserStatsResponseData

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """获取用户统计"""
    user_id = current_user["userId"]
    user_level = current_user.get("userLevel", "normal") # Get from current_user or default

    # Mock data based on the spec
    mock_stats_data = UserStatsResponseData(
        userId=user_id,
        userLevel=user_level,
        currentLevelExp=1250,
        nextLevelExp=2000,
        statistics=UserStatistics(
            totalMessages=current_user.get("totalMessages", 156), # Use from profile or default
            totalLikes=current_user.get("totalLikes", 89),
            totalDays=15,
            roomsCount=len(current_user.get("joinedRooms", [])), # Calculate from profile or default
            favoriteAICount=len(current_user.get("favoriteCharacters", []))
        ),
        achievements=[
            Achievement(
                achievementId="first_message",
                name="初出茅庐",
                description="发送第一条消息",
                unlockTime=time.time() - 86400 # Mocked as unlocked yesterday
            )
        ],
        weeklyStats=WeeklyStats(
            messagesCount=25,
            likesReceived=12,
            likesGiven=18,
            activeHours=5.5
        )
    )
    return UserStatsResponse(data=mock_stats_data)


class CharacterTalent(BaseModel): # Simplified for this context
    skillId: str
    skillName: str
    level: int

class OwnedCharacter(BaseModel):
    characterId: str
    dimension: str
    name: str
    level: int
    experience: int
    nextLevelExp: int
    avatar: str
    talents: List[CharacterTalent] # Simplified, spec shows more detail
    learnedSkills: List[CharacterTalent] # Simplified, spec shows more detail
    isActive: bool = False

class CharacterPreview(BaseModel): # Simplified, spec shows more detail
    talents: List[str]
    specialSkills: List[str]
    sampleDialogue: str

class AvailableCharacter(BaseModel):
    characterId: str
    dimension: str
    name: str
    unlockType: str
    price: Optional[float] = None # Price if unlockType is 'paid'
    preview: Optional[CharacterPreview] = None # Simplified

class LockedCharacter(BaseModel):
    characterId: str
    name: str
    unlockCondition: str
    preview: Optional[CharacterPreview] = None # Simplified

class UserCharactersResponseData(BaseModel):
    ownedCharacters: List[OwnedCharacter]
    availableCharacters: List[AvailableCharacter]
    lockedCharacters: List[LockedCharacter]

class UserCharactersResponse(BaseModel):
    code: int = 200
    data: UserCharactersResponseData

@router.get("/characters", response_model=UserCharactersResponse)
async def get_user_characters(request: Request, current_user: dict = Depends(get_current_user)):
    """获取用户角色库"""
    user_id = current_user["userId"]

    # Mock data based on the spec
    base = build_base_url(request, force_https=True)
    mock_owned_characters = [
        OwnedCharacter(
            characterId="intj_scientist_001",
            dimension="INTJ",
            name="艾米·科学家",
            level=15,
            experience=2580,
            nextLevelExp=3000,
            avatar= base + "/static/ui/icons/icon-wisdom.svg",
            talents=[
                CharacterTalent(skillId="data_analysis", skillName="数据分析", level=5),
                CharacterTalent(skillId="logical_reasoning", skillName="逻辑推理", level=4)
            ],
            learnedSkills=[
                CharacterTalent(skillId="investment_analysis", skillName="投资分析", level=3)
            ],
            isActive=True
        )
    ]

    mock_available_characters = [
        AvailableCharacter(
            characterId="intj_architect_002",
            dimension="INTJ",
            name="大卫·建筑师",
            unlockType="paid",
            price=12,
            preview=CharacterPreview(
                talents=["空间设计", "美学感知"],
                specialSkills=["建筑分析"],
                sampleDialogue="让我们从结构和美学的角度来分析这个问题..."
            )
        )
    ]

    mock_locked_characters = [
        LockedCharacter(
            characterId="intj_strategist_004",
            name="莉莉·战略家",
            unlockCondition="VIP等级",
            preview=CharacterPreview(
                talents=["战略规划", "风险评估"],
                specialSkills=["决策分析"],
                sampleDialogue="每一个决策都可能影响未来格局。"
            )
        )
    ]

    response_data = UserCharactersResponseData(
        ownedCharacters=mock_owned_characters,
        availableCharacters=mock_available_characters,
        lockedCharacters=mock_locked_characters
    )

    return UserCharactersResponse(data=response_data)
