"""
技能系统API路由
"""
from fastapi import APIRouter, Depends, HTTPException # Added Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List # Added List
import time # Added time for mock data

router = APIRouter()

# Placeholder for JWT token dependency
async def get_current_user_placeholder(token: Optional[str] = Depends(lambda x: x.headers.get("Authorization"))):
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = token.split("_")[-1]
        return {"userId": user_id, "userLevel": "normal"}
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid token format for mock")

# --- Mock User Skill Data & Character Skill Definitions ---
# This would typically come from a database
# User's current skill levels and experience for a specific character
# Key: (user_id, character_id, skill_id)
mock_user_skill_progress = {
    ("user_123", "intj_scientist_001", "data_analysis"): {"level": 2, "experience": 150, "maxLevel": 10},
    ("user_123", "intj_scientist_001", "logical_reasoning"): {"level": 1, "experience": 50, "maxLevel": 10},
    ("user_123", "intj_scientist_001", "investment_analysis"): {"level": 0, "experience": 0, "maxLevel": 10} # Learnable, not yet leveled
}

# General skill definitions (simplified, could be part of character definition)
# For simplicity, let's assume fixed XP per level and cost. In reality, this would be complex.
skill_upgrade_rules = {
    "data_analysis": {"xp_per_level": [100, 200, 300, 400, 500, 600, 700, 800, 900], "cost_per_level": [10, 20, 30, 40, 50, 60, 70, 80, 90]},
    "logical_reasoning": {"xp_per_level": [80, 160, 240], "cost_per_level": [5, 15, 25]},
    "investment_analysis": {"xp_per_level": [120, 250, 400], "cost_per_level": [100, 200, 300]} # Higher cost for learnable skills
}

# Mock user resources
fake_user_resources = {
    "user_123": {"skill_points": 100, "gold": 1000}
}

# --- Pydantic Models for Skill Upgrade ---
class SkillUpgradeRequest(BaseModel):
    characterId: str
    skillId: str
    # upgradeType: Optional[str] = "experience" # Could be 'experience', 'fast_upgrade_points', 'item'

class SkillUpgradeResponseData(BaseModel):
    characterId: str
    skillId: str
    newLevel: int
    newExperience: int
    maxLevel: int
    message: str
    # resourcesSpent: Optional[dict] = None

class SkillUpgradeResponse(BaseModel):
    code: int = 200
    data: SkillUpgradeResponseData

# --- Pydantic Models for Skill Progress --- 
class CharacterSkillProgressDetail(BaseModel):
    skillId: str
    skillName: str # Added for better display
    skillType: str # e.g., "talent", "learnable"
    level: int
    experience: int
    maxLevel: int
    xpToNextLevel: Optional[int] = None # XP needed to reach current_level + 1
    description: str
    isUnlocked: bool
    unlockConditionDescription: Optional[str] = None
    canUpgrade: bool # Based on resources and XP
    upgradeCostDescription: Optional[str] = None # e.g. "100 Gold, 50 Skill Points"

class GetSkillProgressResponseData(BaseModel):
    characterId: str
    skills: List[CharacterSkillProgressDetail]

class GetSkillProgressResponse(BaseModel):
    code: int = 200
    data: GetSkillProgressResponseData

# Need access to character definitions to know all their skills
# This would ideally be loaded from a shared character data module/service
mock_character_definitions_for_skills = {
    "intj_scientist_001": {
        "talents": [
            {"skillId": "data_analysis", "skillName": "数据分析", "maxLevel": 10, "description": "天生擅长分析复杂数据和发现规律"},
            {"skillId": "logical_reasoning", "skillName": "逻辑推理", "maxLevel": 10, "description": "严密的逻辑思维和推理能力"}
        ],
        "learnableSkills": [
            {"skillId": "investment_analysis", "skillName": "投资分析", "maxLevel": 10, "description": "通过学习掌握的投资分析技巧", "unlockCondition": {"type": "level", "requirement": 5, "description": "角色等级达到5级"}}
        ]
    }
}

@router.get("/progress/{character_id}", response_model=GetSkillProgressResponse)
async def get_skill_progress(character_id: str, current_user: dict = Depends(get_current_user_placeholder)):
    """获取角色技能进度"""
    user_id = f"user_{current_user['userId']}"

    char_def = mock_character_definitions_for_skills.get(character_id)
    if not char_def:
        raise HTTPException(status_code=404, detail=f"Character definition for '{character_id}' not found.")

    user_skills_details = []

    # Process talents
    for talent_def in char_def.get("talents", []):
        skill_id = talent_def["skillId"]
        user_skill_key = (user_id, character_id, skill_id)
        progress = mock_user_skill_progress.get(user_skill_key, {"level": 0, "experience": 0}) # Default if no progress
        
        current_level = progress.get("level", 0)
        max_lvl = talent_def.get("maxLevel", 10)
        xp_needed = None
        can_upgrade = False
        upgrade_cost_desc = "N/A"

        if current_level < max_lvl:
            rules = skill_upgrade_rules.get(skill_id)
            if rules and current_level < len(rules["xp_per_level"]):
                xp_needed = rules["xp_per_level"][current_level]
                cost = rules["cost_per_level"][current_level]
                user_res = fake_user_resources.get(user_id, {"skill_points": 0})
                if user_res.get("skill_points", 0) >= cost: # Simplified: only checks skill points
                    can_upgrade = True # Assuming XP is also met or not a requirement for this check
                upgrade_cost_desc = f"{cost} Skill Points"
            else:
                 upgrade_cost_desc = "Max level or rules undefined"
        else:
            upgrade_cost_desc = "Max Level Reached"

        user_skills_details.append(CharacterSkillProgressDetail(
            skillId=skill_id,
            skillName=talent_def.get("skillName", skill_id),
            skillType="talent",
            level=current_level,
            experience=progress.get("experience", 0),
            maxLevel=max_lvl,
            xpToNextLevel=xp_needed,
            description=talent_def.get("description", ""),
            isUnlocked=True, # Talents are inherently unlocked
            canUpgrade=can_upgrade,
            upgradeCostDescription=upgrade_cost_desc
        ))

    # Process learnable skills
    for learnable_def in char_def.get("learnableSkills", []):
        skill_id = learnable_def["skillId"]
        user_skill_key = (user_id, character_id, skill_id)
        progress = mock_user_skill_progress.get(user_skill_key, {"level": 0, "experience": 0})
        
        current_level = progress.get("level", 0)
        max_lvl = learnable_def.get("maxLevel", 10)
        # For learnable skills, isUnlocked might depend on a condition
        # Mocking a simple unlock condition based on character level (not implemented here, assume true for now if progress exists)
        is_unlocked_for_user = user_skill_key in mock_user_skill_progress # Simplified: if entry exists, assume unlocked for leveling
        unlock_desc = learnable_def.get("unlockCondition", {}).get("description")

        xp_needed = None
        can_upgrade = False
        upgrade_cost_desc = "N/A"

        if is_unlocked_for_user and current_level < max_lvl:
            rules = skill_upgrade_rules.get(skill_id)
            if rules and current_level < len(rules["xp_per_level"]):
                xp_needed = rules["xp_per_level"][current_level]
                cost = rules["cost_per_level"][current_level]
                user_res = fake_user_resources.get(user_id, {"skill_points": 0})
                if user_res.get("skill_points", 0) >= cost:
                    can_upgrade = True
                upgrade_cost_desc = f"{cost} Skill Points"
            else:
                upgrade_cost_desc = "Max level or rules undefined"
        elif not is_unlocked_for_user:
            upgrade_cost_desc = "Skill not unlocked"
        else: # Unlocked but max level
            upgrade_cost_desc = "Max Level Reached"

        user_skills_details.append(CharacterSkillProgressDetail(
            skillId=skill_id,
            skillName=learnable_def.get("skillName", skill_id),
            skillType="learnable",
            level=current_level,
            experience=progress.get("experience", 0),
            maxLevel=max_lvl,
            xpToNextLevel=xp_needed,
            description=learnable_def.get("description", ""),
            isUnlocked=is_unlocked_for_user,
            unlockConditionDescription=unlock_desc if not is_unlocked_for_user else None,
            canUpgrade=can_upgrade,
            upgradeCostDescription=upgrade_cost_desc
        ))

    return GetSkillProgressResponse(data=GetSkillProgressResponseData(
        characterId=character_id,
        skills=user_skills_details
    ))

@router.post("/upgrade", response_model=SkillUpgradeResponse)
async def upgrade_skill(request: SkillUpgradeRequest, current_user: dict = Depends(get_current_user_placeholder)):
    """技能升级"""
    user_id = f"user_{current_user['userId']}"
    char_id = request.characterId
    skill_id_to_upgrade = request.skillId

    user_skill_key = (user_id, char_id, skill_id_to_upgrade)

    if user_skill_key not in mock_user_skill_progress:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id_to_upgrade}' not found for character '{char_id}' for this user, or character not owned/valid.")

    current_skill_data = mock_user_skill_progress[user_skill_key]
    current_level = current_skill_data["level"]
    current_xp = current_skill_data["experience"]
    max_level = current_skill_data["maxLevel"]

    if current_level >= max_level:
        return SkillUpgradeResponse(code=400, data=SkillUpgradeResponseData(
            characterId=char_id, skillId=skill_id_to_upgrade, newLevel=current_level, newExperience=current_xp, maxLevel=max_level,
            message="Skill is already at max level."
        ))

    skill_rules = skill_upgrade_rules.get(skill_id_to_upgrade)
    if not skill_rules:
        raise HTTPException(status_code=500, detail=f"Upgrade rules for skill '{skill_id_to_upgrade}' not defined.")

    # Simplified: Assume upgrade always means leveling up if XP is sufficient
    # In a real game, XP accumulates and then you spend resources to level up.
    # Here, let's assume this endpoint is called when XP is enough OR it's a direct level purchase.
    # For this mock, let's assume it's a direct level purchase using 'skill_points'.

    xp_needed_for_next_level = skill_rules["xp_per_level"][current_level] if current_level < len(skill_rules["xp_per_level"]) else float('inf')
    cost_for_next_level = skill_rules["cost_per_level"][current_level] if current_level < len(skill_rules["cost_per_level"]) else float('inf')

    # Check if user has enough resources (e.g., skill points)
    user_res = fake_user_resources.get(user_id, {"skill_points": 0})
    if user_res.get("skill_points", 0) < cost_for_next_level:
        return SkillUpgradeResponse(code=400, data=SkillUpgradeResponseData(
            characterId=char_id, skillId=skill_id_to_upgrade, newLevel=current_level, newExperience=current_xp, maxLevel=max_level,
            message=f"Insufficient skill points. Need {cost_for_next_level}, have {user_res.get('skill_points', 0)}."
        ))
    
    # Deduct resources and upgrade skill
    user_res["skill_points"] -= cost_for_next_level
    current_skill_data["level"] += 1
    current_skill_data["experience"] = 0 # Reset XP for the new level or adjust based on game logic

    # Update mock database (in a real app, this would be a DB transaction)
    mock_user_skill_progress[user_skill_key] = current_skill_data
    fake_user_resources[user_id] = user_res

    return SkillUpgradeResponse(data=SkillUpgradeResponseData(
        characterId=char_id,
        skillId=skill_id_to_upgrade,
        newLevel=current_skill_data["level"],
        newExperience=current_skill_data["experience"],
        maxLevel=max_level,
        message=f"Skill '{skill_id_to_upgrade}' upgraded to level {current_skill_data['level']}."
    ))
