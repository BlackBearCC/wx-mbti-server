from fastapi import APIRouter, Request
import structlog
from app.utils.url import build_base_url

router = APIRouter()
logger = structlog.get_logger("home_api")

# 预生成的首页卡片数据
_cards = [
    {
        "id": "finance_room",
        "title": "金融投资",
        # Gen-Z 黄黑主题背景（SVG）
        "background": "url(/static/ui/bg/bg-room.svg) center/cover no-repeat",
        "icon": "/static/ui/icons/icon-wisdom.svg",
        "description": "专业金融分析，投资理财建议",
        "roomId": "finance_room",
        "targetUrl": ""
    },
    {
        "id": "entertainment_room",
        "title": "娱乐休闲",
        "background": "url(/static/ui/bg/bg-chat.svg) center/cover no-repeat",
        "icon": "/static/ui/icons/icon-joy.svg",
        "description": "轻松聊天，娱乐互动",
        "roomId": "entertainment_room",
        "targetUrl": ""
    },
]

# 预生成的首页轮播图数据
_swipers = [
    {
        "id": "banner_finance_001",
        "imageUrl": "/static/ui/bg/bg-room.svg",
        "title": "投资热门话题",
        "jumpType": "room",
        "roomId": "finance_room",
    },
    {
        "id": "banner_outside_001",
        "imageUrl": "/static/ui/bg/bg-chat.svg",
        "title": "活动推荐",
        "jumpType": "url",
        "targetUrl": "https://example.com/activity",
    },
]


@router.get("/home/cards", summary="获取首页卡片列表", tags=["Home"])
async def get_home_cards(request: Request):
    logger.info("home_cards_called", client=str(request.client.host))
    base = build_base_url(request, force_https=True)
    cards = []
    for c in _cards:
        bg = c.get("background", "")
        # 将 url(/static/...) 替换为绝对 URL
        if bg.startswith("url(/"):
            bg_abs = "url(" + base + bg[4:]  # 4 == len('url(')
        else:
            bg_abs = bg
        item = dict(c)
        item["background"] = bg_abs
        icon = item.get("icon") or ""
        if icon.startswith("/"):
            item["icon"] = base + icon
        elif not icon:
            item["icon"] = base + "/static/ui/icons/icon-joy.svg"
        cards.append(item)
    return {"code": 200, "data": {"cards": cards}}


@router.get("/home/swipers", summary="获取首页轮播图列表", tags=["Home"])
async def get_home_swipers(request: Request):
    logger.info("home_swipers_called", client=str(request.client.host))
    base = build_base_url(request, force_https=True)
    sw = []
    for s in _swipers:
        item = dict(s)
        url = item.get("imageUrl")
        if url and url.startswith("/"):
            item["imageUrl"] = base + url
        sw.append(item)
    return {"code": 200, "data": {"swipers": sw}}
