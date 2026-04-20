#!/bin/bash

# AI教育平台 Docker 部署脚本
# 使用方法: ./deploy.sh [选项]
# 选项:
#   build   - 构建镜像
#   start   - 启动服务
#   stop    - 停止服务
#   restart - 重启服务
#   logs    - 查看日志
#   clean   - 清理容器和镜像

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_info "Docker 环境检查通过"
}

# 检查 .env 文件
check_env() {
    if [ ! -f .env ]; then
        print_error ".env 文件不存在"
        print_info "请创建 .env 文件并配置必要的环境变量"
        exit 1
    fi
    print_info ".env 文件检查通过"
}

# 构建镜像
build_image() {
    print_info "开始构建 Docker 镜像..."
    docker-compose build --no-cache
    print_info "镜像构建完成"
}

# 启动服务
start_service() {
    print_info "启动服务..."
    docker-compose up -d
    print_info "服务启动成功"
    print_info "访问地址: http://localhost:8000"
    print_info "查看日志: ./deploy.sh logs"
}

# 停止服务
stop_service() {
    print_info "停止服务..."
    docker-compose down
    print_info "服务已停止"
}

# 重启服务
restart_service() {
    print_info "重启服务..."
    docker-compose restart
    print_info "服务重启完成"
}

# 查看日志
view_logs() {
    print_info "查看服务日志 (Ctrl+C 退出)..."
    docker-compose logs -f --tail=100
}

# 查看服务状态
check_status() {
    print_info "服务状态:"
    docker-compose ps
}

# 清理容器和镜像
clean_all() {
    print_warn "这将删除所有容器、镜像和未使用的卷"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "停止并删除容器..."
        docker-compose down -v
        
        print_info "删除镜像..."
        docker rmi $(docker images -q ai-education-platform) 2>/dev/null || true
        
        print_info "清理完成"
    else
        print_info "取消清理操作"
    fi
}

# 备份数据
backup_data() {
    BACKUP_DIR="backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/data_backup_${TIMESTAMP}.tar.gz"
    
    mkdir -p ${BACKUP_DIR}
    
    print_info "开始备份数据..."
    tar -czf ${BACKUP_FILE} data/
    print_info "数据备份完成: ${BACKUP_FILE}"
}

# 恢复数据
restore_data() {
    if [ -z "$1" ]; then
        print_error "请指定备份文件路径"
        print_info "用法: ./deploy.sh restore <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$1" ]; then
        print_error "备份文件不存在: $1"
        exit 1
    fi
    
    print_warn "这将覆盖当前的数据目录"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "恢复数据..."
        tar -xzf "$1"
        print_info "数据恢复完成"
    else
        print_info "取消恢复操作"
    fi
}

# 更新服务
update_service() {
    print_info "更新服务..."
    
    # 备份数据
    backup_data
    
    # 拉取最新代码
    print_info "拉取最新代码..."
    git pull
    
    # 重新构建并启动
    print_info "重新构建镜像..."
    docker-compose build
    
    print_info "重启服务..."
    docker-compose up -d
    
    print_info "更新完成"
}

# 显示帮助信息
show_help() {
    cat << EOF
AI教育平台 Docker 部署脚本

使用方法: ./deploy.sh [命令]

命令:
  build       构建 Docker 镜像
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志
  clean       清理容器和镜像
  backup      备份数据
  restore     恢复数据 (需要指定备份文件)
  update      更新服务 (拉取代码、重新构建、重启)
  help        显示此帮助信息

示例:
  ./deploy.sh build          # 构建镜像
  ./deploy.sh start          # 启动服务
  ./deploy.sh logs           # 查看日志
  ./deploy.sh backup         # 备份数据
  ./deploy.sh restore backup.tar.gz  # 恢复数据

EOF
}

# 主函数
main() {
    # 检查 Docker 环境
    check_docker
    
    # 解析命令
    case "${1:-help}" in
        build)
            check_env
            build_image
            ;;
        start)
            check_env
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        clean)
            clean_all
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$2"
            ;;
        update)
            check_env
            update_service
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
