"""
角色管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import time
from app.utils.url import build_base_url

router = APIRouter()

# Placeholder for JWT token dependency (can be shared or defined in a common utility)
async def get_current_user_placeholder(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    token = authorization
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Mock user extraction
    try:
        user_id = token.split("_")[-1] # e.g. Bearer mock_jwt_token_for_user_123 -> 123
        return {"userId": user_id, "userLevel": "normal"} # Return a mock user dict
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid token format for mock")

# --- Mock Character Data Store ---
# This would typically come from a database
mock_characters_db = {
    "intj_scientist_001": {
        "characterId": "intj_scientist_001",
        "dimension": "INTJ",
        "name": "艾米·科学家",
        "englishName": "Amy Scientist",
        # 使用服务端内置 PNG 图标（兼容小程序 http/https 限制）
        # 切换为 Gen-Z 黄黑主题图标（SVG）
        "avatar": "/static/ui/icons/icon-wisdom.svg",
        "background": "科学家",
        "backgroundStory": "毕业于斯坦福大学的数据科学博士，专注于复杂系统分析...",
        "rarity": "common",
        "unlockType": "free",
        "price": 0,
        "personality": {
            "traits": ["理性", "独立", "追求真理", "完美主义"],
            "catchphrase": "数据不会撒谎，但解读数据需要智慧",
            "communication": "逻辑清晰，喜欢用事实和数据说话",
            "quirks": ["喜欢用比喻解释复杂概念", "偶尔会陷入思考忘记回复"]
        },
        "talents": [
            {
                "skillId": "data_analysis", "skillName": "数据分析", "level": 1, "maxLevel": 10,
                "experience": 0, "description": "天生擅长分析复杂数据和发现规律",
                "effects": {"level1": "基础数据解读能力", "level5": "高级统计分析能力", "level10": "预测建模大师级能力"}
            },
            {
                "skillId": "logical_reasoning", "skillName": "逻辑推理", "level": 1, "maxLevel": 10,
                "experience": 0, "description": "严密的逻辑思维和推理能力"
            }
        ],
        "learnableSkills": [
            {
                "skillId": "investment_analysis", "skillName": "投资分析", "level": 0, "maxLevel": 10,
                "experience": 0,
                "unlockCondition": {"type": "topic_interaction", "topics": ["投资", "股票"], "requirement": 50},
                "upgradeConditions": [] # Simplified for now
            }
        ],
        "statistics": {"totalMessages": 1256, "totalLikes": 890, "topicExpertise": {"science": 0.95}},
        "isEnabled": True, "createTime": time.time(), "updateTime": time.time()
    }
    # Add more mock characters as needed
}

# --- Pydantic Models for Character Detail Endpoint ---
class CharacterPersonality(BaseModel):
    traits: List[str]
    catchphrase: str
    communication: str
    quirks: List[str]

class CharacterSkillEffect(BaseModel):
    level1: Optional[str] = None
    level5: Optional[str] = None
    level10: Optional[str] = None

class CharacterTalentDetail(BaseModel):
    skillId: str
    skillName: str
    level: int
    maxLevel: int
    experience: int
    description: str
    effects: Optional[CharacterSkillEffect] = None # Made optional as not all talents might have it in spec

class CharacterLearnableSkillUnlockCondition(BaseModel):
    type: str
    topics: Optional[List[str]] = None
    roomId: Optional[str] = None
    requirement: int
    description: Optional[str] = None

class CharacterLearnableSkillDetail(BaseModel):
    skillId: str
    skillName: str
    level: int # User's current level for this skill with this character
    maxLevel: int
    experience: int
    unlockCondition: CharacterLearnableSkillUnlockCondition
    # upgradeConditions: List[Dict] # Simplified for now

class CharacterStatistics(BaseModel):
    totalMessages: int
    totalLikes: int
    averageResponseTime: Optional[float] = None
    userRating: Optional[float] = None
    topicExpertise: Dict[str, float]

class CharacterDetailData(BaseModel):
    characterId: str
    dimension: str
    name: str
    englishName: Optional[str] = None
    avatar: str
    background: str
    backgroundStory: str
    rarity: str
    unlockType: str
    price: Optional[float] = None
    personality: CharacterPersonality
    talents: List[CharacterTalentDetail]
    learnableSkills: List[CharacterLearnableSkillDetail] # This should reflect general learnable skills, not user progress here
    statistics: CharacterStatistics
    isEnabled: bool
    createTime: float
    updateTime: float

class UserSkillProgress(BaseModel):
    skillId: str
    level: int
    experience: int
    nextLevelExp: int
    canUpgrade: bool
    fastUpgradeCost: Optional[float] = None

class UserCharacterProgress(BaseModel):
    level: int
    experience: int
    nextLevelExp: int
    skillProgress: List[UserSkillProgress]
    recentAchievements: List[str]

class GetCharacterDetailResponseData(BaseModel):
    character: CharacterDetailData
    userProgress: UserCharacterProgress

class GetCharacterDetailResponse(BaseModel):
    code: int = 200
    data: GetCharacterDetailResponseData

@router.get("/{character_id}", response_model=GetCharacterDetailResponse)
async def get_character_detail(character_id: str, current_user: dict = Depends(get_current_user_placeholder)):
    """获取角色详情"""
    character_data = mock_characters_db.get(character_id)
    if not character_data:
        raise HTTPException(status_code=404, detail="Character not found")

    # Adapt learnable skills from general character data to the response model
    # For this endpoint, learnableSkills on CharacterDetailData should show general info
    # User's progress on these skills is in userProgress.skillProgress
    processed_learnable_skills = []
    for skill_template in character_data.get("learnableSkills", []):
        processed_learnable_skills.append(
            CharacterLearnableSkillDetail(
                skillId=skill_template["skillId"],
                skillName=skill_template["skillName"],
                level=0, # Base level before user interaction
                maxLevel=skill_template["maxLevel"],
                experience=0, # Base experience
                unlockCondition=CharacterLearnableSkillUnlockCondition(**skill_template["unlockCondition"])
            )
        )
    
    character_detail_for_response = CharacterDetailData(
        **character_data, # Unpack most fields
        learnableSkills=processed_learnable_skills # Use processed list
    )

    # Mock user progress for this character
    # In a real app, this would be fetched from a user-character specific table
    mock_user_progress = UserCharacterProgress(
        level=15, # From spec example
        experience=2580,
        nextLevelExp=3000,
        skillProgress=[
            UserSkillProgress(
                skillId="investment_analysis",
                level=3,
                experience=245,
                nextLevelExp=300,
                canUpgrade=True,
                fastUpgradeCost=6
            )
        ],
        recentAchievements=["投资分析师", "连续对话7天", "获得100个认同"]
    )

    response_data = GetCharacterDetailResponseData(
        character=character_detail_for_response,
        userProgress=mock_user_progress
    )
    return GetCharacterDetailResponse(data=response_data)


# --- Pydantic Models for Character Shop Listing ---
class ShopCharacter(BaseModel):
    characterId: str
    name: str
    avatar: str
    dimension: str
    rarity: str # e.g., common, rare, epic, legendary
    unlockType: str # e.g., free, points, iap
    price: Optional[float] = None # Only if unlockType is points or iap
    tags: List[str] = []
    isOwned: bool # Indicates if the current user owns this character
    isNew: bool = False
    discount: Optional[str] = None # e.g., "限时免费", "首周8折"

class GetShopCharactersResponseData(BaseModel):
    characters: List[ShopCharacter]
    # Potentially add pagination or filter metadata here in the future

class GetShopCharactersResponse(BaseModel):
    code: int = 200
    data: GetShopCharactersResponseData

# --- Pydantic Models for Character Unlock Endpoint ---
class UnlockCharacterRequest(BaseModel):
    characterId: str
    # unlockMethod: Optional[str] = "points" # Could be 'points', 'iap_receipt_id', etc.

class UnlockCharacterResponseData(BaseModel):
    characterId: str
    unlockStatus: str # e.g., "success", "already_owned", "insufficient_funds", "not_found"
    message: Optional[str] = None
    # newBalance: Optional[float] = None # If unlocking with points

class UnlockCharacterResponse(BaseModel):
    code: int = 200
    data: UnlockCharacterResponseData

# Mock user data store (simplified)
fake_users_inventory = {
    "user_123": {
        "owned_characters": ["intj_scientist_001"],
        "points_balance": 5000 
    }
}

@router.get("/", response_model=GetShopCharactersResponse) # Added response_model
async def get_characters(request: Request, current_user: dict = Depends(get_current_user_placeholder)): # Added current_user dependency
    """获取角色列表 (角色商店)"""
    # Mock user's owned characters - in a real app, this comes from user data
    user_owned_characters = ["intj_scientist_001"] # Example: user owns this character

    shop_characters_list = []
    base = build_base_url(request, force_https=True)
    for char_id, char_data in mock_characters_db.items():
        if not char_data.get("isEnabled", True): # Skip disabled characters
            continue

        avatar = char_data["avatar"]
        if avatar.startswith("/"):
            avatar = base + avatar
        shop_char = ShopCharacter(
            characterId=char_data["characterId"],
            name=char_data["name"],
            avatar=avatar,
            dimension=char_data["dimension"],
            rarity=char_data["rarity"],
            unlockType=char_data["unlockType"],
            price=char_data.get("price"),
            tags=char_data.get("personality", {}).get("traits", [])[:2], # Example: use first 2 traits as tags
            isOwned=char_id in user_owned_characters,
            isNew= (time.time() - char_data.get("createTime", 0)) < (7 * 24 * 60 * 60), # New if created in last 7 days
            # discount logic can be added here if needed
        )
        shop_characters_list.append(shop_char)
    
    # Add a couple more mock characters for the shop, not necessarily in full detail in mock_characters_db
    # These would typically also come from the main character database
    if "infp_dreamer_002" not in mock_characters_db:
        shop_characters_list.append(ShopCharacter(
            characterId="infp_dreamer_002",
            name="露娜·梦想家",
            avatar= base + "/static/ui/icons/icon-empathy.svg",
            dimension="INFP",
            rarity="rare",
            unlockType="points",
            price=1200,
            tags=["理想主义", "共情"],
            isOwned=False,
            isNew=True,
            discount="首周8折"
        ))
    if "estj_commander_003" not in mock_characters_db:
        shop_characters_list.append(ShopCharacter(
            characterId="estj_commander_003",
            name="马库斯·指挥官",
            avatar= base + "/static/ui/icons/icon-focus.svg",
            dimension="ESTJ",
            rarity="epic",
            unlockType="iap", # In-app purchase
            price=29.99, # Could be a reference to an IAP product ID
            tags=["果断", "领导力"],
            isOwned=False
        ))

    response_data = GetShopCharactersResponseData(characters=shop_characters_list)
    return GetShopCharactersResponse(data=response_data)


@router.post("/unlock", response_model=UnlockCharacterResponse)
async def unlock_character(request: UnlockCharacterRequest, current_user: dict = Depends(get_current_user_placeholder)):
    """解锁角色"""
    user_id = f"user_{current_user['userId']}" # Construct user ID for mock db
    character_id_to_unlock = request.characterId

    # Ensure user exists in our mock db, if not, add them (for testing)
    if user_id not in fake_users_inventory:
        fake_users_inventory[user_id] = {"owned_characters": [], "points_balance": 10000} # Give new mock users some points

    user_data = fake_users_inventory[user_id]

    # Check if character exists
    target_character = mock_characters_db.get(character_id_to_unlock)
    if not target_character:
        # Also check the additional mock characters added for shop display
        if character_id_to_unlock == "infp_dreamer_002":
            target_character = {"characterId": "infp_dreamer_002", "unlockType": "points", "price": 1200, "name": "露娜·梦想家"}
        elif character_id_to_unlock == "estj_commander_003":
            target_character = {"characterId": "estj_commander_003", "unlockType": "iap", "price": 29.99, "name": "马库斯·指挥官"}
        else:
            raise HTTPException(status_code=404, detail=f"Character '{character_id_to_unlock}' not found.")

    # Check if already owned
    if character_id_to_unlock in user_data["owned_characters"]:
        return UnlockCharacterResponse(data=UnlockCharacterResponseData(
            characterId=character_id_to_unlock,
            unlockStatus="already_owned",
            message=f"Character '{target_character.get('name', character_id_to_unlock)}' is already owned."
        ))

    unlock_type = target_character.get("unlockType")
    price = target_character.get("price", 0)

    if unlock_type == "free":
        user_data["owned_characters"].append(character_id_to_unlock)
        return UnlockCharacterResponse(data=UnlockCharacterResponseData(
            characterId=character_id_to_unlock,
            unlockStatus="success",
            message=f"Free character '{target_character.get('name', character_id_to_unlock)}' unlocked successfully."
        ))
    elif unlock_type == "points":
        if user_data["points_balance"] >= price:
            user_data["points_balance"] -= price
            user_data["owned_characters"].append(character_id_to_unlock)
            return UnlockCharacterResponse(data=UnlockCharacterResponseData(
                characterId=character_id_to_unlock,
                unlockStatus="success",
                message=f"Character '{target_character.get('name', character_id_to_unlock)}' unlocked with {price} points. New balance: {user_data['points_balance']}",
                # newBalance=user_data["points_balance"]
            ))
        else:
            return UnlockCharacterResponse(code=400, data=UnlockCharacterResponseData(
                characterId=character_id_to_unlock,
                unlockStatus="insufficient_funds",
                message=f"Insufficient points to unlock '{target_character.get('name', character_id_to_unlock)}'. Required: {price}, Available: {user_data['points_balance']}"
            ))
    elif unlock_type == "iap":
        # Here you would typically validate an IAP receipt
        # For mock purposes, we'll assume IAP is successful if requested
        user_data["owned_characters"].append(character_id_to_unlock)
        return UnlockCharacterResponse(data=UnlockCharacterResponseData(
            characterId=character_id_to_unlock,
            unlockStatus="success", # Assuming IAP validation is successful
            message=f"Character '{target_character.get('name', character_id_to_unlock)}' (IAP) unlocked successfully. (Mocked)"
        ))
    else:
        raise HTTPException(status_code=500, detail=f"Unknown unlock type '{unlock_type}' for character '{character_id_to_unlock}'.")
