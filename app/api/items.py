from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Placeholder for user authentication dependency
async def get_current_user_placeholder():
    # In a real app, this would validate a token and return user info
    return {"userId": "mock_user_123", "username": "testuser"}

router = APIRouter()

# --- Mock Data for Items and Inventory ---
fake_item_definitions: Dict[str, Dict[str, Any]] = {
    "item_xp_boost_small": {"itemId": "item_xp_boost_small", "name": "小型经验药水", "description": "使用后获得少量经验值", "type": "consumable", "effect": {"type": "xp_gain", "amount": 100}},
    "item_gift_rose": {"itemId": "item_gift_rose", "name": "玫瑰花", "description": "赠送给角色可以增加好感度", "type": "gift", "effect": {"type": "affinity_gain", "amount": 10}},
    "item_key_rare": {"itemId": "item_key_rare", "name": "稀有宝箱钥匙", "description": "可以用来开启稀有宝箱", "type": "key"}
}

fake_user_inventory: Dict[str, List[Dict[str, Any]]] = {
    "user_mock_user_123": [
        {"itemId": "item_xp_boost_small", "quantity": 5, "instanceId": "inv_xp_1"},
        {"itemId": "item_gift_rose", "quantity": 2, "instanceId": "inv_rose_1"}
    ]
}

# --- Pydantic Models for Items --- 

class InventoryItemDetail(BaseModel):
    instanceId: str # Unique ID for this stack in inventory
    itemId: str
    name: str
    description: str
    quantity: int
    item_type: str # e.g., consumable, gift, key
    # Other relevant item properties like icon_url, rarity, etc.

class GetInventoryResponseData(BaseModel):
    items: List[InventoryItemDetail]
    total_items: int

class GetInventoryResponse(BaseModel):
    code: int = 200
    data: GetInventoryResponseData

class UseItemRequest(BaseModel):
    instance_id: str # The unique ID of the item stack in inventory
    quantity: int = 1
    target_character_id: Optional[str] = None # For gifts or character-specific items

class UseItemResponseData(BaseModel):
    success: bool
    message: str
    remaining_quantity: int
    # Potentially details about the effect, e.g., xp_gained, affinity_change
    effect_details: Optional[Dict[str, Any]] = None 

class UseItemResponse(BaseModel):
    code: int = 200
    data: UseItemResponseData

@router.get("/inventory", response_model=GetInventoryResponse)
async def get_user_inventory(current_user: dict = Depends(get_current_user_placeholder)):
    """获取用户物品库存"""
    user_id = f"user_{current_user['userId']}"
    user_items = fake_user_inventory.get(user_id, [])
    
    inventory_details = []
    for item_stack in user_items:
        item_def = fake_item_definitions.get(item_stack["itemId"])
        if item_def:
            inventory_details.append(InventoryItemDetail(
                instanceId=item_stack["instanceId"],
                itemId=item_stack["itemId"],
                name=item_def["name"],
                description=item_def["description"],
                quantity=item_stack["quantity"],
                item_type=item_def["type"]
            ))
            
    return GetInventoryResponse(data=GetInventoryResponseData(
        items=inventory_details,
        total_items=len(inventory_details)
    ))

@router.post("/use", response_model=UseItemResponse)
async def use_item(request: UseItemRequest, current_user: dict = Depends(get_current_user_placeholder)):
    """使用物品"""
    user_id = f"user_{current_user['userId']}"
    user_items = fake_user_inventory.get(user_id, [])

    item_to_use_stack = None
    item_idx = -1
    for idx, stack in enumerate(user_items):
        if stack["instanceId"] == request.instance_id:
            item_to_use_stack = stack
            item_idx = idx
            break

    if not item_to_use_stack:
        raise HTTPException(status_code=404, detail="Item not found in inventory.")

    item_def = fake_item_definitions.get(item_to_use_stack["itemId"])
    if not item_def:
        raise HTTPException(status_code=500, detail="Item definition not found.") # Should not happen

    if item_to_use_stack["quantity"] < request.quantity:
        raise HTTPException(status_code=400, detail="Not enough items to use.")

    # Mock item usage logic
    item_to_use_stack["quantity"] -= request.quantity
    effect_details = {"action": f"Used {item_def['name']}"}
    message = f"Successfully used {request.quantity} x {item_def['name']}."

    if item_def["type"] == "consumable" and item_def.get("effect"):
        effect = item_def["effect"]
        if effect["type"] == "xp_gain":
            # In a real app, update user's XP or character's XP
            effect_details["xp_gained"] = effect["amount"] * request.quantity
            message += f" Gained {effect_details['xp_gained']} XP."
    elif item_def["type"] == "gift" and item_def.get("effect"):
        if not request.target_character_id:
            raise HTTPException(status_code=400, detail="Target character ID required for gifts.")
        effect = item_def["effect"]
        if effect["type"] == "affinity_gain":
            # In a real app, update character affinity
            effect_details["affinity_gained_with_character"] = request.target_character_id
            effect_details["affinity_amount"] = effect["amount"] * request.quantity
            message += f" Affinity with {request.target_character_id} increased."
    
    # Remove item stack if quantity is zero
    if item_to_use_stack["quantity"] <= 0:
        user_items.pop(item_idx)
    else:
        user_items[item_idx] = item_to_use_stack # Update the list
    
    fake_user_inventory[user_id] = user_items # Persist changes to mock DB

    return UseItemResponse(data=UseItemResponseData(
        success=True,
        message=message,
        remaining_quantity=item_to_use_stack["quantity"],
        effect_details=effect_details
    ))

# Placeholder for item shop, etc.
# @router.get("/shop")
# async def get_item_shop():
#     return {"message": "Item shop - 待实现"}