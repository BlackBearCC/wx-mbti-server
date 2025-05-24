#!/bin/bash

# 微信小程序AI聊天室后端启动脚本

echo "🚀 启动微信小程序AI聊天室后端服务..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置必要的环境变量（数据库密码、微信配置等）"
    echo "⚠️  配置完成后重新运行此脚本"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p static uploads logs

# 构建并启动服务
echo "🔨 构建并启动服务..."
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 运行数据库迁移
echo "🗄️ 运行数据库迁移..."
docker-compose exec -T app alembic upgrade head

echo "✅ 服务启动完成！"
echo ""
echo "📊 服务访问地址："
echo "  - API文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo "  - Grafana监控: http://localhost:3000 (admin/admin)"
echo "  - Flower任务监控: http://localhost:5555"
echo ""
echo "📝 查看日志："
echo "  docker-compose logs -f app"
echo ""
echo "🛑 停止服务："
echo "  docker-compose down" 