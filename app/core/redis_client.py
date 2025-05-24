"""
Redis客户端配置和连接管理
"""
import redis.asyncio as redis
from typing import Optional, Any, Dict, List
import json
import structlog
from app.config.settings import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Redis连接池
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """初始化Redis连接"""
    global redis_pool, redis_client
    
    try:
        # 创建连接池
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        # 创建Redis客户端
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # 测试连接
        await redis_client.ping()
        
        logger.info("Redis连接初始化成功", url=settings.REDIS_URL)
        
    except Exception as e:
        logger.error("Redis连接初始化失败", error=str(e))
        raise


async def close_redis():
    """关闭Redis连接"""
    global redis_pool, redis_client
    
    try:
        if redis_client:
            await redis_client.aclose()
            
        if redis_pool:
            await redis_pool.aclose()
            
        logger.info("Redis连接已关闭")
        
    except Exception as e:
        logger.error("关闭Redis连接时出错", error=str(e))


def get_redis() -> redis.Redis:
    """获取Redis客户端实例"""
    if redis_client is None:
        raise RuntimeError("Redis客户端未初始化")
    return redis_client


class RedisService:
    """Redis服务封装类"""
    
    def __init__(self):
        self.client = get_redis()
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error("Redis GET失败", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            return await self.client.set(key, value, ex=expire)
        except Exception as e:
            logger.error("Redis SET失败", key=key, error=str(e))
            return False
    
    async def delete(self, *keys: str) -> int:
        """删除键"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE失败", keys=keys, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error("Redis EXISTS失败", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis EXPIRE失败", key=key, error=str(e))
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增"""
        try:
            return await self.client.incr(key, amount)
        except Exception as e:
            logger.error("Redis INCR失败", key=key, error=str(e))
            return None
    
    async def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """递减"""
        try:
            return await self.client.decr(key, amount)
        except Exception as e:
            logger.error("Redis DECR失败", key=key, error=str(e))
            return None
    
    # Hash操作
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """设置哈希字段"""
        try:
            # 转换值为JSON字符串
            json_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    json_mapping[k] = json.dumps(v, ensure_ascii=False)
                else:
                    json_mapping[k] = str(v)
            
            return await self.client.hset(name, mapping=json_mapping)
        except Exception as e:
            logger.error("Redis HSET失败", name=name, error=str(e))
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段值"""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error("Redis HGET失败", name=name, key=key, error=str(e))
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段"""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error("Redis HGETALL失败", name=name, error=str(e))
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """删除哈希字段"""
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error("Redis HDEL失败", name=name, keys=keys, error=str(e))
            return 0
    
    # 列表操作
    async def lpush(self, name: str, *values: Any) -> int:
        """左侧插入列表"""
        try:
            json_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    json_values.append(json.dumps(v, ensure_ascii=False))
                else:
                    json_values.append(str(v))
            
            return await self.client.lpush(name, *json_values)
        except Exception as e:
            logger.error("Redis LPUSH失败", name=name, error=str(e))
            return 0
    
    async def rpop(self, name: str) -> Optional[str]:
        """右侧弹出列表元素"""
        try:
            return await self.client.rpop(name)
        except Exception as e:
            logger.error("Redis RPOP失败", name=name, error=str(e))
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表范围"""
        try:
            return await self.client.lrange(name, start, end)
        except Exception as e:
            logger.error("Redis LRANGE失败", name=name, error=str(e))
            return []
    
    # 集合操作
    async def sadd(self, name: str, *values: Any) -> int:
        """添加集合元素"""
        try:
            str_values = [str(v) for v in values]
            return await self.client.sadd(name, *str_values)
        except Exception as e:
            logger.error("Redis SADD失败", name=name, error=str(e))
            return 0
    
    async def srem(self, name: str, *values: Any) -> int:
        """删除集合元素"""
        try:
            str_values = [str(v) for v in values]
            return await self.client.srem(name, *str_values)
        except Exception as e:
            logger.error("Redis SREM失败", name=name, error=str(e))
            return 0
    
    async def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error("Redis SMEMBERS失败", name=name, error=str(e))
            return set()
    
    async def sismember(self, name: str, value: Any) -> bool:
        """检查是否为集合成员"""
        try:
            return await self.client.sismember(name, str(value))
        except Exception as e:
            logger.error("Redis SISMEMBER失败", name=name, value=value, error=str(e))
            return False
    
    # 发布订阅
    async def publish(self, channel: str, message: Any) -> int:
        """发布消息"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message, ensure_ascii=False)
            
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.error("Redis PUBLISH失败", channel=channel, error=str(e))
            return 0
    
    async def subscribe(self, *channels: str):
        """订阅频道"""
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error("Redis SUBSCRIBE失败", channels=channels, error=str(e))
            return None


# 全局Redis服务实例
def get_redis_service() -> RedisService:
    """获取Redis服务实例"""
    return RedisService() 