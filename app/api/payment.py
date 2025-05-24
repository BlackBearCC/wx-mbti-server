"""
支付系统API路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/create-order")
async def create_order():
    """创建订单"""
    return {"message": "创建订单API - 待实现"}


@router.post("/callback")
async def payment_callback():
    """支付回调"""
    return {"message": "支付回调API - 待实现"}
