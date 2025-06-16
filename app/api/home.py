from fastapi import APIRouter, Request
import structlog

router = APIRouter()
logger = structlog.get_logger("home_api")

# 预生成的首页卡片数据
_cards = [
    {
        "id": "finance_room",
        "title": "金融投资",
        "icon": "💰",
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "description": "专业金融分析，投资理财建议",
        "roomId": "finance_room",
        "targetUrl": ""
    },
    {
        "id": "entertainment_room",
        "title": "娱乐休闲",
        "icon": "🎮",
        "background": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "description": "轻松聊天，娱乐互动",
        "roomId": "entertainment_room",
        "targetUrl": ""
    },
]

# 预生成的首页轮播图数据
_swipers = [
    {
        "id": "banner_finance_001",
        "imageUrl": "/static/banners/finance.svg",
        "title": "投资热门话题",
        "jumpType": "room",
        "roomId": "finance_room",
    },
    {
        "id": "banner_outside_001",
        "imageUrl": "/static/banners/promo.svg",
        "jumpType": "url",
        "targetUrl": "https://example.com/activity",
    },
]


@router.get("/home/cards", summary="获取首页卡片列表", tags=["Home"])
async def get_home_cards(request: Request):
    logger.info("home_cards_called", client=str(request.client.host))
    return {
        "code": 200,
        "data": {
            "cards": _cards,
        },
    }


@router.get("/home/swipers", summary="获取首页轮播图列表", tags=["Home"])
async def get_home_swipers(request: Request):
    logger.info("home_swipers_called", client=str(request.client.host))
    return {
        "code": 200,
        "data": {
            "swipers": _swipers,
        },
    } 