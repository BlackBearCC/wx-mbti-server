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

from app.config.settings import get_settings
from app.config.database import init_db, close_db
from app.core.redis_client import init_redis, close_redis
from app.core.websocket_manager import WebSocketManager
from app.api import auth, users, characters, rooms, skills, payment, websocket
from app.utils.exceptions import AppException

# 获取配置
settings = get_settings()

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json"
        else structlog.processors.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.LOG_LEVEL.upper(), structlog.INFO)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# WebSocket管理器
websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("应用启动中...", app_name=settings.APP_NAME, version=settings.APP_VERSION)
    
    try:
        # 初始化数据库
        await init_db()
        logger.info("数据库初始化完成")
        
        # 初始化Redis
        await init_redis()
        logger.info("Redis初始化完成")
        
        # 创建静态文件目录
        os.makedirs(settings.STATIC_FILES_PATH, exist_ok=True)
        os.makedirs(settings.UPLOAD_FILES_PATH, exist_ok=True)
        
        logger.info("应用启动完成")
        
        yield
        
    except Exception as e:
        logger.error("应用启动失败", error=str(e))
        raise
    finally:
        # 关闭时清理
        logger.info("应用关闭中...")
        
        try:
            await close_redis()
            logger.info("Redis连接已关闭")
            
            await close_db()
            logger.info("数据库连接已关闭")
            
        except Exception as e:
            logger.error("应用关闭时出错", error=str(e))
        
        logger.info("应用已关闭")


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
app.mount("/static", StaticFiles(directory=settings.STATIC_FILES_PATH), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_FILES_PATH), name="uploads")

# API路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/user", tags=["用户"])
app.include_router(characters.router, prefix="/api/characters", tags=["角色"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["聊天室"])
app.include_router(skills.router, prefix="/api/skills", tags=["技能"])
app.include_router(payment.router, prefix="/api/payment", tags=["支付"])

# WebSocket路由
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

# 健康检查端点
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """根路径信息"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "微信小程序AI聊天室后端API",
        "docs_url": "/docs" if settings.DEBUG else None
    }


# Prometheus指标端点（如果启用监控）
if settings.PROMETHEUS_METRICS_PATH:
    try:
        from prometheus_client import make_asgi_app
        metrics_app = make_asgi_app()
        app.mount(settings.PROMETHEUS_METRICS_PATH, metrics_app)
    except ImportError:
        logger.warning("prometheus_client 未安装，跳过指标端点")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG
    ) 