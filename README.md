# 微信小程序AI聊天室后端服务

基于FastAPI的高性能AI聊天室后端服务，支持多维度MBTI角色生态系统。

## 🏗️ 技术架构

### 核心技术栈
- **Web框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15+ (主库) + Redis 7+ (缓存)
- **WebSocket**: FastAPI WebSocket + Redis Pub/Sub
- **认证**: JWT + 微信小程序认证
- **容器化**: Docker + Docker Compose

### 架构设计
```
┌─────────────────┐    ┌─────────────────┐
│   微信小程序      │    │   FastAPI       │
│                │ -> │   API服务        │
│   WebSocket     │    │   WebSocket     │
└─────────────────┘    └─────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
      ┌─────────▼────────┐    ┌─────────▼────────┐
      │   PostgreSQL     │    │     Redis        │
      │   用户/角色/消息   │    │   缓存/会话       │
      │   技能/订单数据    │    │   Pub/Sub       │
      └──────────────────┘    └──────────────────┘
```

## 📁 项目结构

```
wx-mbti-server/
├── app/                        # 应用核心代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config/                 # 配置文件
│   │   ├── __init__.py
│   │   ├── settings.py         # 应用配置
│   │   └── database.py         # 数据库配置
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入
│   │   ├── auth.py             # 认证相关
│   │   ├── users.py            # 用户管理
│   │   ├── characters.py       # 角色管理
│   │   ├── rooms.py            # 聊天室管理
│   │   ├── skills.py           # 技能系统
│   │   ├── payment.py          # 支付系统
│   │   └── websocket.py        # WebSocket处理
│   ├── core/                   # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py         # 安全相关
│   │   ├── redis_client.py     # Redis客户端
│   │   └── websocket_manager.py # WebSocket管理器
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── character.py
│   │   ├── room.py
│   │   ├── message.py
│   │   ├── skill.py
│   │   └── order.py
│   ├── schemas/                # Pydantic模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── character.py
│   │   ├── room.py
│   │   ├── message.py
│   │   ├── skill.py
│   │   └── websocket.py
│   ├── services/               # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── character_service.py
│   │   ├── skill_service.py
│   │   ├── room_service.py
│   │   ├── message_service.py
│   │   ├── payment_service.py
│   │   └── ai_service.py
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── validators.py
│       ├── decorators.py
│       └── exceptions.py
├── migrations/                 # 数据库迁移
├── tests/                      # 测试代码
├── scripts/                    # 数据库脚本
├── docker/                     # Docker配置
├── requirements.txt            # Python依赖
├── docker-compose.yml          # 容器编排
├── Dockerfile                  # 镜像构建
├── .env.example               # 环境变量示例
└── alembic.ini                # 数据库迁移配置
```

## 🚀 快速开始

### 本地开发环境

1. **克隆项目**
```bash
git clone <repository-url>
cd wx-mbti-server
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件配置数据库连接等信息
```

3. **使用Docker Compose启动服务**
```bash
docker-compose up -d
```

4. **运行数据库迁移**
```bash
docker-compose exec app alembic upgrade head
```

5. **访问服务**
- API文档: http://localhost:8000/docs
- 应用服务: http://localhost:8000

## 🔧 开发指南

### API开发
- 遵循RESTful设计原则
- 使用Pydantic进行数据验证
- 实现完整的错误处理
- 添加API文档和测试

### 数据库操作
- 使用SQLAlchemy ORM
- 通过Alembic管理数据库迁移
- 实现数据库连接池

### WebSocket通信
- 基于FastAPI WebSocket
- Redis Pub/Sub实现多实例消息广播
- 心跳检测和自动重连

### 测试
```bash
# 运行单元测试
pytest tests/

# 运行集成测试
pytest tests/integration/

# 生成测试覆盖率报告
pytest --cov=app tests/
```

## 🔐 安全考虑

- JWT token认证
- 请求频率限制
- SQL注入防护
- XSS防护
- CORS配置
- 敏感信息加密

## 📈 性能优化

- Redis缓存策略
- 数据库查询优化
- WebSocket连接池管理
- 异步任务处理

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交代码并测试
4. 创建Pull Request

## 📄 License

MIT License