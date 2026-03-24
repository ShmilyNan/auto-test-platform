#!/bin/bash
# ============================================
# Celery Worker 启动脚本
# 包含依赖检查和优雅关闭
# ============================================

set -e

echo "=========================================="
echo "Celery Worker 启动脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 等待依赖服务
wait_for_redis() {
    local host="${REDIS_HOST:-localhost}"
    local port="${REDIS_PORT:-6379}"
    local max_attempts=30
    local attempt=1

    log_info "等待 Redis 服务: $host:$port"

    while [ $attempt -le $max_attempts ]; do
        if python3 -c "import redis; redis.Redis(host='$host', port=$port, socket_timeout=5).ping()" 2>/dev/null; then
            log_info "✅ Redis 连接成功"
            return 0
        fi

        log_warn "Redis 未就绪，等待中... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "Redis 连接超时"
    return 1
}

wait_for_postgres() {
    local host="${DATABASE_HOST:-localhost}"
    local port="${DATABASE_PORT:-5432}"
    local max_attempts=30
    local attempt=1

    log_info "等待 PostgreSQL 服务: $host:$port"

    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
result = s.connect_ex(('$host', $port))
s.close()
exit(0 if result == 0 else 1)
" 2>/dev/null; then
            log_info "✅ PostgreSQL 连接成功"
            return 0
        fi

        log_warn "PostgreSQL 未就绪，等待中... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "PostgreSQL 连接超时"
    return 1
}

# 检查 Python 依赖
check_dependencies() {
    log_info "检查 Python 依赖..."

    local missing=0
    local packages=("celery" "redis" "loguru" "pydantic" "sqlalchemy" "asyncpg")

    for pkg in "${packages[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            log_error "缺少依赖: $pkg"
            missing=1
        fi
    done

    if [ $missing -eq 1 ]; then
        log_warn "正在安装缺失的依赖..."
        pip install -q celery redis loguru pydantic sqlalchemy asyncpg 2>/dev/null || true
    fi

    log_info "✅ 依赖检查完成"
}

# 信号处理
cleanup() {
    log_warn "收到关闭信号，正在优雅关闭..."

    # 发送 Warm Shutdown 信号给 Celery
    if [ -n "$WORKER_PID" ]; then
        kill -TERM "$WORKER_PID" 2>/dev/null || true
        wait "$WORKER_PID" 2>/dev/null || true
    fi

    log_info "Worker 已关闭"
    exit 0
}

# 注册信号处理
trap cleanup SIGTERM SIGINT SIGQUIT

# 主流程
main() {
    log_info "启动参数: $*"

    # 检查依赖
    check_dependencies

    # 等待 Redis
    if ! wait_for_redis; then
        log_error "无法连接到 Redis，退出"
        exit 1
    fi

    # 等待 PostgreSQL（可选，用于任务执行）
    if [ "${SKIP_POSTGRES:-false}" != "true" ]; then
        wait_for_postgres || log_warn "PostgreSQL 连接失败，将在任务执行时重试"
    fi

    log_info "=========================================="
    log_info "启动 Celery Worker"
    log_info "=========================================="

    # 启动 Celery Worker
    # --without-gossip: 禁用 gossip 消息减少网络开销
    # --without-mingle: 禁用 mingle 减少启动时间
    # --without-heartbeat: 禁用心跳（使用 Redis 作为心跳检测）
    exec celery -A scheduler worker \
        --loglevel="${CELERY_LOG_LEVEL:-info}" \
        --concurrency="${CELERY_WORKER_CONCURRENCY:-4}" \
        --max-tasks-per-child="${CELERY_MAX_TASKS_PER_CHILD:-100}" \
        --without-gossip \
        --without-mingle \
        "$@"
}

# 执行
main "$@"
