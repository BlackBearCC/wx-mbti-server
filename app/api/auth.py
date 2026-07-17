"""
认证相关API路由
- 开发模式（无真实 AppID）：用 code 哈希生成 openid，跳过微信 API
- 正式模式：调用微信 jscode2session 获取 openid
两种模式都会 find-or-create 用户入 PostgreSQL，并签发真实 JWT
"""
import hashlib
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import get_settings
from app.core.jwt import create_access_token
from app.models.user import User, UserLevel

router = APIRouter()
settings = get_settings()


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
    openid: str
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


async def _get_openid_via_wechat(code: str) -> str:
    """调用微信 jscode2session 获取 openid"""
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if "openid" not in data:
        raise HTTPException(status_code=400, detail=f"微信登录失败: {data.get('errmsg', 'unknown')}")
    return data["openid"]


def _get_openid_dev(code: str) -> str:
    """开发模式：用 code 哈希生成稳定的 openid"""
    raw = f"dev_openid_{code}_{settings.WECHAT_APPID}"
    return "dev_" + hashlib.md5(raw.encode()).hexdigest()[:24]


@router.post("/wxlogin", response_model=WxLoginResponse)
async def wechat_login(request_data: WxLoginRequest, db: AsyncSession = Depends(get_db)):
    """微信小程序登录"""
    # 判断是否使用开发模式
    use_dev_mode = (
        not settings.WECHAT_APPID
        or settings.WECHAT_APPID.startswith("wx1234567890")
        or settings.DEBUG
    )

    if use_dev_mode:
        openid = _get_openid_dev(request_data.code)
    else:
        openid = await _get_openid_via_wechat(request_data.code)

    # find-or-create 用户
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(
            openid=openid,
            nick_name=request_data.nickName or "WeChat User",
            avatar_url=request_data.avatarUrl or "",
            gender=request_data.gender or 0,
            country=request_data.country or "",
            province=request_data.province or "",
            city=request_data.city or "",
            user_level=UserLevel.NORMAL,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # 更新登录信息
        user.last_login_time = time.time()
        if request_data.nickName:
            user.nick_name = request_data.nickName
        if request_data.avatarUrl:
            user.avatar_url = request_data.avatarUrl
        await db.commit()
        await db.refresh(user)

    # 签发 JWT
    token = create_access_token(user.user_id)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    user_info = UserInfo(
        userId=user.user_id,
        openid=user.openid,
        nickName=user.nick_name,
        avatarUrl=user.avatar_url or "",
        userLevel=user.user_level.value if user.user_level else "normal",
        createTime=user.create_time.timestamp() if user.create_time else time.time(),
        lastLoginTime=user.last_login_time.timestamp() if user.last_login_time else time.time(),
        isNewUser=is_new,
    )

    default_characters = [
        DefaultCharacter(characterId="intj_scientist_001", dimension="INTJ", name="艾米·科学家"),
    ]

    response_data = WxLoginResponseData(
        token=token,
        expiresIn=expires_in,
        user=user_info,
        defaultCharacters=default_characters,
    )
    return WxLoginResponse(data=response_data)


@router.post("/refresh")
async def refresh_token():
    """刷新token"""
    return {"message": "刷新token API - 待实现"}


@router.post("/logout")
async def logout():
    """退出登录"""
    return {"message": "退出登录 API - 待实现"}
