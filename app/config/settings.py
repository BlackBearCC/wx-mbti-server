"""
应用配置管理
"""
from functools import lru_cache
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import validator, Field
import os
import json

# 项目根目录
# app/config/settings.py -> app/ -> project_root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "wx-mbti-server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # 数据库配置
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return (
            f"postgresql+asyncpg://"
            f"{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}"
            f"@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}"
            f"/{values.get('POSTGRES_DB')}"
        )
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get('REDIS_PASSWORD') else ""
        return f"redis://{password_part}{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
    
    # Celery配置
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # 微信小程序配置
    WECHAT_APPID: str
    WECHAT_SECRET: str
    
    # 微信支付配置
    WECHAT_PAY_MCHID: Optional[str] = None
    WECHAT_PAY_KEY: Optional[str] = None
    WECHAT_PAY_CERT_PATH: Optional[str] = None
    WECHAT_PAY_KEY_PATH: Optional[str] = None
    
    # AI服务配置
    AI_DEFAULT_PROVIDER: str = "doubao"
    AI_FALLBACK_PROVIDER: Optional[str] = None
    AI_STREAM_ENABLED: bool = True
    AI_MAX_OUTPUT_TOKENS: int = 1024
    AI_PROVIDER_OVERRIDES: Optional[str] = None  # JSON字符串，用于配置多供应商
    AI_MODEL_ALIASES: Optional[str] = None  # JSON字符串，定义友好名称与模型映射
    AI_DEFAULT_MODEL_ALIAS: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "ep-20240901-chatglm-3-6b"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = Field(default_factory=list)
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # JSON格式
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # 如果JSON解析失败，作为逗号分隔字符串处理
                    return [i.strip() for i in v.split(",") if i.strip()]
            else:
                # 逗号分隔字符串
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        else:
            return []
    
    # 文件存储配置
    STATIC_FILES_PATH: str = os.path.join(PROJECT_ROOT, "static")
    UPLOAD_FILES_PATH: str = os.path.join(PROJECT_ROOT, "uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 心跳间隔(秒)
    WS_MAX_CONNECTIONS_PER_USER: int = 5  # 每用户最大连接数
    
    # 业务配置
    DEFAULT_FREE_CHARACTERS: int = 16  # 默认免费角色数
    MAX_MESSAGE_LENGTH: int = 1000  # 最大消息长度
    MAX_ROOM_MEMBERS: int = 100  # 房间最大人数
    AI_RESPONSE_TIMEOUT: int = 30  # AI响应超时时间(秒)

    # 简易鉴权配置（以 API Token 形式）。多个 token 用逗号分隔或 JSON 数组。
    API_TOKENS: Optional[str] = None
    # 开发模式下若未配置 API_TOKENS，是否允许任意非空 token 通过（便于本地联调）
    AUTH_ALLOW_ANY_TOKEN_IN_DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置实例"""
    return Settings()
