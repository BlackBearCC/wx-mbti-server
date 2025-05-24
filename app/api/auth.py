"""
认证相关API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/wxlogin")
async def wechat_login():
    """微信小程序登录"""
    return {"message": "微信登录API - 待实现"}


@router.post("/refresh")
async def refresh_token():
    """刷新token"""
    return {"message": "刷新token API - 待实现"}


@router.post("/logout") 
async def logout():
    """退出登录"""
    return {"message": "退出登录API - 待实现"} 