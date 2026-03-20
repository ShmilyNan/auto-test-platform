#!/bin/bash

# ============================================
# Docker Swarm 服务故障排查脚本
# 适用于 WSL Ubuntu 环境
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}"; }

STACK_NAME="autotest"

echo "======================================"
echo "Docker Swarm 服务故障排查"
echo "WSL Ubuntu 环境"
echo "======================================"

# ============================================
# 1. 环境检查
# ============================================
log_section "1. 环境检查"

echo -e "\n${YELLOW}1.1 系统信息${NC}"
echo "系统: $(uname -a)"
echo "发行版: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"

echo -e "\n${YELLOW}1.2 Docker 安装检查${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null)
    log_info "Docker 已安装: $DOCKER_VERSION"
else
    log_error "Docker 未安装或不在 PATH 中"

    # 检查 Docker Desktop
    if [ -f "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe" ]; then
        log_warn "检测到 Docker Desktop，请确保："
        echo "  1. Docker Desktop 正在运行"
        echo "  2. 已启用 WSL 2 集成（Settings > Resources > WSL Integration）"
        echo "  3. 已将当前 WSL 发行版添加到集成列表"
    fi
    exit 1
fi

echo -e "\n${YELLOW}1.3 Docker 连接检查${NC}"
if docker info &> /dev/null; then
    log_info "Docker 守护进程连接正常"
else
    log_error "无法连接到 Docker 守护进程"
    log_info "可能的原因："
    echo "  1. Docker Desktop 未运行"
    echo "  2. Docker 服务未启动"
    echo "  3. 用户不在 docker 组"

    # 检查 docker.sock
    if [ -S /var/run/docker.sock ]; then
        log_info "docker.sock 存在"
        ls -la /var/run/docker.sock
    else
        log_error "docker.sock 不存在"
    fi
    exit 1
fi

# ============================================
# 2. Docker Swarm 状态检查
# ============================================
log_section "2. Docker Swarm 状态检查"

echo -e "\n${YELLOW}2.1 Swarm 模式状态${NC}"
SWARM_STATUS=$(docker info 2>/dev/null | grep "Swarm:" | awk '{print $2}')
if [ "$SWARM_STATUS" = "active" ]; then
    log_info "Swarm 模式已激活"

    echo -e "\n${YELLOW}2.2 节点信息${NC}"
    docker node ls

    echo -e "\n${YELLOW}2.3 当前节点详情${NC}"
    NODE_ID=$(docker node ls --filter role=manager -q | head -1)
    if [ -n "$NODE_ID" ]; then
        docker node inspect $NODE_ID --format '{{.Description.Hostname}} {{.Status.State}} {{.Spec.Availability}}'
    fi
else
    log_error "Swarm 模式未激活"
    log_info "运行以下命令初始化: docker swarm init"
    exit 1
fi

# ============================================
# 3. 服务状态检查
# ============================================
log_section "3. 服务状态检查"

echo -e "\n${YELLOW}3.1 服务列表${NC}"
if docker service ls 2>/dev/null | grep -q "$STACK_NAME"; then
    docker service ls --filter name=$STACK_NAME

    echo -e "\n${YELLOW}3.2 服务任务状态${NC}"
    docker stack ps $STACK_NAME --no-trunc 2>/dev/null || log_warn "服务栈不存在"

    echo -e "\n${YELLOW}3.3 失败任务详情${NC}"
    FAILED_TASKS=$(docker stack ps $STACK_NAME --filter desired-state=failed -q 2>/dev/null)
    if [ -n "$FAILED_TASKS" ]; then
        for task in $FAILED_TASKS; do
            echo "--- 任务 $task ---"
            docker service ps --no-trunc $task 2>/dev/null | head -20
        done
    else
        log_info "没有失败的任务"
    fi
else
    log_warn "未找到 $STACK_NAME 服务栈"
fi

# ============================================
# 4. 网络检查
# ============================================
log_section "4. 网络检查"

echo -e "\n${YELLOW}4.1 Docker 网络列表${NC}"
docker network ls

echo -e "\n${YELLOW}4.2 Overlay 网络检查${NC}"
if docker network inspect autotest-network &> /dev/null; then
    log_info "autotest-network 网络存在"
    docker network inspect autotest-network --format '{{.Scope}} {{.Driver}}'
else
    log_warn "autotest-network 网络不存在"
fi

# ============================================
# 5. 挂载路径检查（WSL 重点）
# ============================================
log_section "5. 挂载路径检查"

echo -e "\n${YELLOW}5.1 检查数据目录是否存在${NC}"
REQUIRED_DIRS=(
    "/data/autotest/postgres"
    "/data/autotest/redis"
    "/data/autotest/storage"
    "/data/autotest/logs"
    "/data/autotest/allure-results"
    "/data/autotest/allure-report"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        log_info "$dir 存在"
        ls -la "$dir" | head -3
    else
        log_error "$dir 不存在"
        log_info "创建命令: sudo mkdir -p $dir"
    fi
done

echo -e "\n${YELLOW}5.2 目录权限检查${NC}"
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        PERMS=$(stat -c "%a %U:%G" "$dir" 2>/dev/null || stat -f "%OLp %Su:%Sg" "$dir" 2>/dev/null)
        echo "$dir: $PERMS"
    fi
done

echo -e "\n${YELLOW}5.3 磁盘空间检查${NC}"
df -h /data 2>/dev/null || df -h /

# ============================================
# 6. Secrets 检查
# ============================================
log_section "6. Secrets 检查"

echo -e "\n${YELLOW}6.1 Docker Secrets 列表${NC}"
docker secret ls

echo -e "\n${YELLOW}6.2 必需的 Secrets 检查${NC}"
REQUIRED_SECRETS=(
    "autotest_postgres_password"
    "autotest_secret_key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if docker secret inspect "$secret" &> /dev/null; then
        log_info "$secret 存在"
    else
        log_error "$secret 不存在"
    fi
done

echo -e "\n${YELLOW}6.3 本地 Secrets 文件检查${NC}"
if [ -d "secrets" ]; then
    for f in secrets/*.txt; do
        if [ -f "$f" ]; then
            if grep -qi "your_" "$f" 2>/dev/null; then
                log_error "$f 包含模板值，请修改"
            else
                log_info "$f 已配置"
            fi
        fi
    done
else
    log_warn "secrets 目录不存在"
fi

# ============================================
# 7. 镜像检查
# ============================================
log_section "7. 镜像检查"

echo -e "\n${YELLOW}7.1 本地镜像列表${NC}"
docker images | head -20

echo -e "\n${YELLOW}7.2 检查项目镜像${NC}"
if docker images | grep -q "autotest-platform"; then
    log_info "autotest-platform 镜像存在"
else
    log_warn "autotest-platform 镜像不存在"
    log_info "构建命令: docker build -t autotest-platform:latest ."
fi

# ============================================
# 8. 服务日志分析
# ============================================
log_section "8. 服务日志分析"

SERVICES=("api" "postgres" "redis" "celery-worker" "celery-beat" "nginx")

for svc in "${SERVICES[@]}"; do
    SERVICE_NAME="${STACK_NAME}_${svc}"
    if docker service ls --filter name=$SERVICE_NAME -q 2>/dev/null | grep -q .; then
        echo -e "\n${YELLOW}=== $SERVICE_NAME 日志 (最后 30 行) ===${NC}"
        docker service logs $SERVICE_NAME --tail 30 2>/dev/null || echo "无法获取日志"
    fi
done

# ============================================
# 9. WSL 特有问题检查
# ============================================
log_section "9. WSL 特有问题检查"

echo -e "\n${YELLOW}9.1 WSL 版本${NC}"
if [ -f /proc/version ]; then
    cat /proc/version | grep -i microsoft && log_info "运行在 WSL 中" || log_warn "可能不是 WSL 环境"
fi

echo -e "\n${YELLOW}9.2 Docker Desktop WSL 集成${NC}"
if [ -L "$HOME/.docker" ]; then
    log_info ".docker 是符号链接（Docker Desktop 集成）"
    ls -la "$HOME/.docker"
fi

echo -e "\n${YELLOW}9.3 CIFS/NTFS 挂载检查${NC}"
mount | grep -E "C:|D:|drvfs" | head -5

echo -e "\n${YELLOW}9.4 /etc/wsl.conf 检查${NC}"
if [ -f /etc/wsl.conf ]; then
    cat /etc/wsl.conf
else
    log_warn "/etc/wsl.conf 不存在"
fi

echo -e "\n${YELLOW}9.5 常见 WSL Docker 问题${NC}"
echo "1. 路径问题: /data 路径在 WSL 中可能不存在"
echo "2. 权限问题: WSL 中文件权限可能与 Windows 不同"
echo "3. 端口问题: Windows 防火墙可能阻止端口访问"
echo "4. 内存问题: WSL 默认内存限制可能过低"

# ============================================
# 10. 端口检查
# ============================================
log_section "10. 端口检查"

echo -e "\n${YELLOW}10.1 检查端口占用${NC}"
PORTS=(80 443 5000 5432 6379)
for port in "${PORTS[@]}"; do
    if ss -tuln 2>/dev/null | grep -q ":${port} "; then
        log_warn "端口 $port 已被占用"
        ss -tuln | grep ":${port} "
    else
        log_info "端口 $port 可用"
    fi
done

# ============================================
# 11. 总结和建议
# ============================================
log_section "11. 问题诊断总结"

echo -e "\n${YELLOW}常见问题及解决方案:${NC}"

echo -e "\n${GREEN}问题1: 服务一直处于 Pending 状态${NC}"
echo "原因: 没有满足约束条件的节点"
echo "解决: 检查 docker-stack.yml 中的 placement constraints"

echo -e "\n${GREEN}问题2: 服务启动后立即失败${NC}"
echo "原因: 镜像不存在或路径挂载失败"
echo "解决: "
echo "  1. 先构建镜像: docker build -t autotest-platform:latest ."
echo "  2. 检查挂载路径是否存在"

echo -e "\n${GREEN}问题3: 数据库连接失败${NC}"
echo "原因: postgres 服务未就绪或 secrets 未配置"
echo "解决:"
echo "  1. 确保 postgres 服务正常运行"
echo "  2. 检查 secrets 是否创建"

echo -e "\n${GREEN}问题4: WSL 路径问题${NC}"
echo "原因: docker-stack.yml 中的 bind mount 路径不存在"
echo "解决:"
echo "  1. 创建数据目录: sudo mkdir -p /data/autotest/{postgres,redis,storage,logs,allure-results,allure-report}"
echo "  2. 或修改 docker-stack.yml 使用 docker volume 代替 bind mount"

echo -e "\n${YELLOW}建议: 使用简化版配置测试${NC}"
echo "运行以下命令获取简化配置:"
echo "  ./scripts/deploy-wsl.sh"
