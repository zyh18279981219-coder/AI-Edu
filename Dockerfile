# 多阶段构建 Dockerfile
# 阶段1: 构建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend-vue/package*.json ./

# 安装依赖
RUN npm ci --legacy-peer-deps

# 复制前端源码
COPY frontend-vue/ ./

# 构建前端
RUN npm run build

# 阶段2: 构建后端运行环境
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend-vue/dist

# 创建必要的目录
RUN mkdir -p data/Log data/Book data/chroma_db data/learning_plans data/digital_twins/history

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV APP_RELOAD=false

# 启动命令
CMD ["python", "main.py"]
