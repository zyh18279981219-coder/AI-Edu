# AI教育平台 Docker 部署指南

## 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 🚀 快速开始

### 1. 安装 Docker（如果未安装）

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 配置环境变量

确保 `.env` 文件存在并配置正确：

```bash
# 检查 .env 文件
cat .env

# 必需的环境变量：
# - model_name
# - base_url
# - api_key
# - embedding_model
```

### 3. 部署服务

```bash
# 给部署脚本添加执行权限
chmod +x deploy.sh

# 构建镜像
./deploy.sh build

# 启动服务
./deploy.sh start

# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs
```

## 📝 部署脚本命令

| 命令 | 说明 |
|------|------|
| `./deploy.sh build` | 构建 Docker 镜像 |
| `./deploy.sh start` | 启动服务 |
| `./deploy.sh stop` | 停止服务 |
| `./deploy.sh restart` | 重启服务 |
| `./deploy.sh status` | 查看服务状态 |
| `./deploy.sh logs` | 查看服务日志 |
| `./deploy.sh clean` | 清理容器和镜像 |
| `./deploy.sh backup` | 备份数据 |
| `./deploy.sh restore <file>` | 恢复数据 |
| `./deploy.sh update` | 更新服务（拉取代码+重新构建） |

## 🔧 手动部署（不使用脚本）

### 构建镜像
```bash
docker-compose build
```

### 启动服务
```bash
docker-compose up -d
```

### 查看日志
```bash
docker-compose logs -f
```

### 停止服务
```bash
docker-compose down
```

## 🌐 访问服务

服务启动后，访问：
- **前端页面**: http://your-server-ip:8000
- **API文档**: http://your-server-ip:8000/docs

## 📦 数据持久化

以下目录会被持久化到宿主机：
- `./data` - 所有数据文件（数据库、日志、上传文件等）

## 🔄 更新部署

### 方式1: 使用部署脚本（推荐）
```bash
./deploy.sh update
```

### 方式2: 手动更新
```bash
# 1. 备份数据
./deploy.sh backup

# 2. 拉取最新代码
git pull

# 3. 重新构建
docker-compose build

# 4. 重启服务
docker-compose up -d
```

## 🛡️ 生产环境建议

### 1. 使用 Nginx 反向代理

创建 `nginx.conf`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 接口
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 文件上传大小限制
    client_max_body_size 100M;
}
```

### 2. 配置 HTTPS（使用 Let's Encrypt）

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 设置防火墙

```bash
# 允许 HTTP 和 HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果直接暴露 8000 端口（不推荐）
sudo ufw allow 8000/tcp

# 启用防火墙
sudo ufw enable
```

### 4. 配置自动备份

创建 cron 任务：
```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点备份
0 2 * * * cd /path/to/project && ./deploy.sh backup
```

### 5. 监控和日志

```bash
# 查看容器资源使用
docker stats

# 查看实时日志
docker-compose logs -f --tail=100

# 导出日志到文件
docker-compose logs > logs_$(date +%Y%m%d).txt
```

## 🐛 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查容器状态
docker-compose ps

# 检查端口占用
sudo netstat -tulpn | grep 8000
```

### 内存不足

```bash
# 查看 Docker 资源使用
docker stats

# 清理未使用的镜像和容器
docker system prune -a
```

### 数据库连接失败

```bash
# 检查数据目录权限
ls -la data/

# 重置数据库（谨慎操作）
./deploy.sh stop
rm -rf data/app.db
./deploy.sh start
```

### 前端无法访问

```bash
# 检查前端构建是否成功
docker-compose logs | grep "frontend"

# 重新构建
./deploy.sh build
./deploy.sh restart
```

## 📊 性能优化

### 1. 调整 Docker 资源限制

修改 `docker-compose.yml`:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 2. 使用生产级 WSGI 服务器

已使用 uvicorn，可以调整 worker 数量：

修改 `main.py`:
```python
uvicorn.run(
    "backend.app:app",
    host="0.0.0.0",
    port=8000,
    workers=4,  # 根据 CPU 核心数调整
    reload=False
)
```

### 3. 启用 Redis 缓存（可选）

在 `docker-compose.yml` 中添加 Redis 服务：
```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: ai-education-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - ai-education-network

volumes:
  redis-data:
```

## 🔐 安全建议

1. **不要将 .env 文件提交到 Git**
2. **定期更新 Docker 镜像**
3. **使用强密码和 API 密钥**
4. **限制容器权限**
5. **定期备份数据**
6. **监控异常访问**

## 📞 支持

如有问题，请查看：
- 项目文档: `README.md`
- 日志文件: `data/Log/`
- Docker 日志: `docker-compose logs`

## 📄 许可证

请参考项目根目录的 LICENSE 文件
