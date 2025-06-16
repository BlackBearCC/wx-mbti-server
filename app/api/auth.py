"""
认证相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import time

# Placeholder for database/user service and JWT utility
# from app.services.user_service import UserService
# from app.utils.jwt_handler import create_access_token

router = APIRouter()

class WxLoginRequest(BaseModel):
    code: str = Field(..., description="微信登录凭证")
    nickName: str = Field(..., description="用户昵称")
    avatarUrl: str = Field(..., description="用户头像URL")
    gender: int = Field(0, description="性别 0未知 1男 2女")
    country: Optional[str] = Field(None, description="国家")
    province: Optional[str] = Field(None, description="省份")
    city: Optional[str] = Field(None, description="城市")

class UserInfo(BaseModel):
    userId: str
    openid: str # This would typically be fetched from WeChat API
    nickName: str
    avatarUrl: str
    userLevel: str = "normal"
    createTime: float = Field(default_factory=time.time)
    lastLoginTime: float = Field(default_factory=time.time)
    isNewUser: bool = True

class DefaultCharacter(BaseModel):
    characterId: str
    dimension: str
    name: str
    isDefault: bool = True

class WxLoginResponseData(BaseModel):
    token: str
    expiresIn: int
    user: UserInfo
    defaultCharacters: List[DefaultCharacter]

class WxLoginResponse(BaseModel):
    code: int = 200
    message: str = "登录成功"
    data: WxLoginResponseData

@router.post("/wxlogin", response_model=WxLoginResponse)
async def wechat_login(request_data: WxLoginRequest):
    """微信小程序登录"""
    # --- Mocked WeChat API call and user creation --- 
    # In a real application, you would:
    # 1. Use `request_data.code` to call WeChat API to get openid and session_key
    # 2. Check if user exists in DB by openid
    # 3. If not, create a new user
    # 4. If yes, update lastLoginTime
    # 5. Generate JWT token

    mock_openid = f"mock_openid_{request_data.code[:5]}"
    mock_user_id = f"user_{int(time.time())}"

    # Mock user data creation
    user_info = UserInfo(
        userId=mock_user_id,
        openid=mock_openid,
        nickName=request_data.nickName,
        avatarUrl=request_data.avatarUrl,
        # gender, country, province, city could be saved to DB here
    )

    # Mock default characters (as per spec)
    default_characters = [
        DefaultCharacter(characterId="intj_scientist_001", dimension="INTJ", name="艾米·科学家"),
        # Potentially add more default characters if the spec implies 16 free ones
        # For now, adding one as an example based on the spec's response example.
    ]

    # Mock JWT token generation
    # token = create_access_token(data={"sub": user_info.userId}, expires_delta=timedelta(minutes=120))
    mock_token = f"mock_jwt_token_for_{user_info.userId}"
    expires_in = 7200

    response_data = WxLoginResponseData(
        token=mock_token,
        expiresIn=expires_in,
        user=user_info,
        defaultCharacters=default_characters
    )

    return WxLoginResponse(data=response_data)


@router.post("/refresh")
async def refresh_token():
    """刷新token"""
    # This would typically require a valid refresh token
    # and then issue a new access token.
    return {"message": "刷新token API - 待实现"}


@router.post("/logout") 
async def logout():
    """退出登录"""
    # This might involve blacklisting the token on the server side.
    return {"message": "退出登录 API - 待实现"}