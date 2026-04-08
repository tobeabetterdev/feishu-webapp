# 工厂订单数据核对系统 - 安装部署指南

本文档详细介绍了工厂订单数据核对系统的安装、配置和部署流程。

## 目录

- [系统要求](#系统要求)
- [开发环境搭建](#开发环境搭建)
- [Docker 部署](#docker-部署)
- [生产环境配置](#生产环境配置)
- [故障排除](#故障排除)
- [性能优化](#性能优化)

## 系统要求

### 最低配置
- **操作系统**: Windows 10+, Linux, 或 macOS
- **内存**: 4GB RAM
- **磁盘空间**: 2GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **操作系统**: Windows 11, Ubuntu 22.04+, 或 macOS 13+
- **内存**: 8GB+ RAM
- **CPU**: 双核处理器
- **磁盘空间**: 10GB+ SSD

## 开发环境搭建

### 1. 前置软件安装

#### Node.js 和 npm
```bash
# 使用 nvm 安装 (推荐)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 或从官网下载: https://nodejs.org/
```

#### Python
```bash
# Windows: 从官网下载安装
# https://www.python.org/downloads/

# Linux/Mac:
sudo apt-get install python3.11  # Ubuntu/Debian
brew install python@3.11          # macOS
```

#### Git
```bash
# Windows: https://git-scm.com/download/win
# Linux: sudo apt-get install git
# Mac: brew install git
```

### 2. 前端开发环境

#### 安装依赖
```bash
cd feishu-webapp
npm install
```

#### 配置开发服务器
```bash
# 开发模式运行
npm run dev

# 生产模式构建
npm run build

# 预览生产构建
npm run preview
```

#### 前端环境变量
创建 `.env.development` 文件：
```env
VITE_API_URL=http://localhost:8000/api
```

创建 `.env.production` 文件：
```env
VITE_API_URL=/api
```

### 3. 后端开发环境

#### 虚拟环境设置
```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### 安装依赖
```bash
pip install -r requirements.txt
```

#### 后端环境变量
创建 `backend/.env` 文件：
```env
# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=False

# 文件上传配置
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=.xlsx,.xls

# 输出目录
OUTPUT_DIR=outputs
```

#### 启动开发服务器
```bash
# 开发模式 (自动重载)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 数据库配置（可选）

如果需要持久化存储任务数据：

#### PostgreSQL
```bash
# 安装 PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu
brew install postgresql                              # macOS

# 创建数据库
createdb feishu_orders

# 更新 requirements.txt
pip install psycopg2-binary sqlalchemy alembic

# 配置数据库连接字符串
DATABASE_URL=postgresql://user:password@localhost/feishu_orders
```

#### SQLite（开发用）
```bash
# SQLite 不需要额外安装，直接使用
DATABASE_URL=sqlite:///./feishu_orders.db
```

## Docker 部署

### 1. 安装 Docker

#### Windows
1. 下载 Docker Desktop: https://www.docker.com/products/docker-desktop
2. 启用 WSL 2 后端
3. 重启计算机

#### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加当前用户到 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

#### macOS
```bash
# 下载 Docker Desktop
# https://www.docker.com/products/docker-desktop

# 或使用 Homebrew
brew install --cask docker
```

### 2. Docker Compose 部署

#### 基础部署
```bash
# 克隆仓库
git clone <repository-url>
cd feishu-webapp

# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 高级配置
```bash
# 重新构建镜像
docker-compose build --no-cache

# 启动特定服务
docker-compose up -d backend
docker-compose up -d frontend

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh
```

### 3. 生产环境 Docker 配置

#### 创建生产环境配置文件
创建 `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=https://api.yourdomain.com
    restart: unless-stopped
    networks:
      - app-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend/outputs:/app/outputs
      - ./backend/logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - ENVIRONMENT=production
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

#### 启动生产环境
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 生产环境配置

### 1. Nginx 反向代理

#### 配置 SSL/HTTPS
```nginx
# /etc/nginx/sites-available/feishu-orders
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/feishu-orders /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. 系统服务配置

#### 创建 systemd 服务
创建 `/etc/systemd/system/feishu-backend.service`:
```ini
[Unit]
Description=Feishu Orders Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/feishu-webapp/backend
Environment="PATH=/var/www/feishu-webapp/backend/venv/bin"
ExecStart=/var/www/feishu-webapp/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable feishu-backend
sudo systemctl start feishu-backend
sudo systemctl status feishu-backend
```

### 3. 监控和日志

#### 日志配置
```python
# backend/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

#### 日志轮转
创建 `/etc/logrotate.d/feishu-orders`:
```
/var/www/feishu-webapp/backend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload feishu-backend > /dev/null 2>&1 || true
    endscript
}
```

## 故障排除

### 1. 常见问题

#### 问题: 前端无法连接后端
**解决方案:**
```bash
# 检查后端是否运行
curl http://localhost:8000/docs

# 检查 CORS 配置
# 确保 backend/main.py 中 CORS 中间件已配置

# 检查防火墙
sudo ufw allow 8000
```

#### 问题: 文件上传失败
**解决方案:**
```bash
# 检查文件大小限制
# 在 nginx.conf 中添加:
client_max_body_size 10M;

# 在 FastAPI 中检查:
# @router.post("/compare")
# async def create_comparison(
#     factory_file: UploadFile = File(...),
#     ...
# )
```

#### 问题: Docker 容器无法启动
**解决方案:**
```bash
# 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 检查端口占用
netstat -tulpn | grep :8000
netstat -tulpn | grep :80

# 清理并重新构建
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### 2. 性能问题

#### 问题: 处理大文件时内存不足
**解决方案:**
```python
# 使用流式处理
async def process_large_file(file: UploadFile):
    async for chunk in file.chunks():
        # 处理数据块
        pass

# 增加工作进程
uvicorn main:app --workers 4 --limit-concurrency 100
```

#### 问题: 响应时间过长
**解决方案:**
```python
# 添加缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_data(key):
    # 获取数据
    pass

# 使用异步操作
import asyncio
await asyncio.gather(
    process_file1(),
    process_file2()
)
```

## 性能优化

### 1. 前端优化

#### 代码分割
```typescript
// 懒加载路由
const OrderComparison = lazy(() => import('./pages/OrderComparison'))

<Suspense fallback={<Loading />}>
  <OrderComparison />
</Suspense>
```

#### 图片优化
```typescript
// 使用 WebP 格式
<picture>
  <source srcSet="image.webp" type="image/webp" />
  <img src="image.jpg" alt="Description" />
</picture>
```

### 2. 后端优化

#### 数据库查询优化
```python
# 使用索引
CREATE INDEX idx_date ON orders(date);

# 使用连接池
from sqlalchemy.pool import QueuePool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

#### 缓存策略
```python
from functools import lru_cache
import redis

# Redis 缓存
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1000)
def get_customer_mapping(factory_type: str):
    # 获取客户映射
    pass
```

### 3. 系统优化

#### 资源限制
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 安全配置

### 1. 环境变量安全
```bash
# 使用 .env 文件
echo "API_KEY=your_secret_key" >> .env
echo ".env" >> .gitignore
```

### 2. API 认证
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected")
async def protected_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # 验证令牌
    pass
```

## 备份和恢复

### 1. 数据备份
```bash
# 备份输出文件
tar -czf backups/outputs-$(date +%Y%m%d).tar.gz backend/outputs/

# 备份数据库
pg_dump feishu_orders > backups/db-$(date +%Y%m%d).sql
```

### 2. 恢复流程
```bash
# 恢复输出文件
tar -xzf backups/outputs-20250408.tar.gz -C backend/

# 恢复数据库
psql feishu_orders < backups/db-20250408.sql
```

## 更新和维护

### 1. 更新依赖
```bash
# 前端
npm update
npm audit fix

# 后端
pip install --upgrade -r requirements.txt
```

### 2. 版本发布
```bash
# 标记版本
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# 构建生产镜像
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## 支持和帮助

如有问题或需要技术支持，请联系：
- 技术支持邮箱: support@example.com
- 问题追踪: https://github.com/your-repo/issues
- 文档: https://docs.example.com