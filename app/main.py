"""
FastAPI 主应用入口
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import structlog
import time
import os
import logging
from pathlib import Path

from app.config.settings import get_settings
from app.config.database import init_db, close_db
from app.core.redis_client import init_redis, close_redis
from app.core.websocket_manager import WebSocketManager
from app.api import auth, users, characters, rooms, skills, chat, items, feedback, admin, home, service, service_ws
from app.utils.exceptions import AppException

# 获取配置
settings = get_settings()

# 计算项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 处理静态与上传目录路径，确保存在
static_dir = Path(settings.STATIC_FILES_PATH)
if not static_dir.is_absolute():
    static_dir = BASE_DIR / static_dir
static_dir.mkdir(parents=True, exist_ok=True)

upload_dir = Path(settings.UPLOAD_FILES_PATH)
if not upload_dir.is_absolute():
    upload_dir = BASE_DIR / upload_dir
upload_dir.mkdir(parents=True, exist_ok=True)

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(ensure_ascii=False) if settings.LOG_FORMAT == "json"
        else structlog.processors.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# WebSocket管理器
websocket_manager = WebSocketManager()


def print_startup_banner():
    """打印带ASCII艺术的启动横幅"""
    banner = f"""
\033[96m
   ███╗   ███╗██████╗ ████████╗██╗      █████╗ ██╗
   ████╗ ████║██╔══██╗╚══██╔══╝██║     ██╔══██╗██║
   ██╔████╔██║██████╔╝   ██║   ██║     ███████║██║
   ██║╚██╔╝██║██╔══██╗   ██║   ██║     ██╔══██║██║
   ██║ ╚═╝ ██║██████╔╝   ██║   ██║     ██║  ██║██║
   ╚═╝     ╚═╝╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝
\033[0m
\033[93m╔═══════════════════════════════════════════════════════════════╗
║    🧠 AI-Powered MBTI Chat Room v{settings.APP_VERSION} 🤖                ║
║    📡 http://localhost:{settings.PORT} | 📖 /docs | 🔍 /health              ║
╚═══════════════════════════════════════════════════════════════╝\033[0m
\033[92m🎯 Features: 16 MBTI Characters | WebSocket | AI Responses | WeChat\033[0m
\033[94m⚡ Stack: FastAPI + PostgreSQL + Redis + Docker\033[0m
"""
    print(banner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 打印启动横幅
    print_startup_banner()
    
    # 启动时初始化
    logger.info("🚀 应用启动中", app_name=settings.APP_NAME, version=settings.APP_VERSION)
    
    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化Redis
        await init_redis()
        logger.info("✅ Redis初始化完成")
        
        # 创建静态文件目录
        os.makedirs(settings.STATIC_FILES_PATH, exist_ok=True)
        os.makedirs(settings.UPLOAD_FILES_PATH, exist_ok=True)
        
        logger.info("🎉 应用启动完成 - Ready to serve!")
        
        yield
        
    except Exception as e:
        logger.error("💥 应用启动失败", error=str(e))
        raise
    finally:
        # 关闭时清理
        logger.info("🛑 应用关闭中")
        
        try:
            await close_redis()
            logger.info("✅ Redis连接已关闭")
            
            await close_db()
            logger.info("✅ 数据库连接已关闭")
            
        except Exception as e:
            logger.error("❌ 应用关闭时出错", error=str(e))
        
        logger.info("👋 应用已关闭 - See you next time!")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="微信小程序AI聊天室后端API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 注册WebSocket管理器到应用状态
app.state.websocket_manager = websocket_manager

# 中间件配置
# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 会话中间件
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    same_site="strict",
    https_only=not settings.DEBUG
)

# GZIP压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 可信主机中间件（生产环境）
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 生产环境应该设置具体的域名
    )


# 请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间和日志记录"""
    start_time = time.time()
    
    # 记录请求开始
    logger.info(
        "请求开始",
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        client_ip=request.client.host
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        
        # 记录请求完成
        logger.info(
            "请求完成",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s"
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        # 记录请求错误
        logger.error(
            "请求失败",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time=f"{process_time:.4f}s"
        )
        raise


# 全局异常处理
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """自定义业务异常处理"""
    logger.warning(
        "业务异常",
        error_code=exc.error_code,
        message=exc.message,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "detail": exc.detail
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.warning(
        "HTTP异常",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "detail": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(
        "未处理异常",
        error=str(exc),
        type=type(exc).__name__,
        url=str(request.url)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# 静态文件服务
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# API路由
app = FastAPI(
    title="MBTI Character Chat API",
    description="This is the backend API for the MBTI Character Chat application.",
    version="0.1.0"
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/user", tags=["Users"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Rooms"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(home.router, prefix="", tags=["Home"])
app.include_router(service.router, prefix="/service", tags=["Service"])
app.include_router(service_ws.router, prefix="/service", tags=["Service-WS"])

@app.get("/ping", tags=["Health Check"])
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG
    )
