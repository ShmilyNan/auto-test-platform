#!/bin/bash

# ============================================
# WSL 环境一键部署脚本
# ============================================
# 适用于: Windows WSL2 + Docker Desktop
# 使用方式: ./deploy-wsl.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

STACK_NAME="autotest"
COMPOSE_FILE="docker-stack.wsl.yaml"

echo "======================================"
echo "WSL 环境一键部署"
echo "======================================"

# ============================================
# Step 1: 环境检查
# ============================================
echo -e "\n${YELLOW}Step 1: 环境检查${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    echo "请确保 Docker Desktop 已安装并启用 WSL 2 集成"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    log_error "Docker 守护进程未运行"
    echo "请启动 Docker Desktop"
    exit 1
fi
log_info "Docker 运行正常"

# 检查 WSL
if ! grep -qi microsoft /proc/version 2>/dev/null; then
    log_warn "可能不是 WSL 环境，继续部署..."
else
    log_info "WSL 环境检测通过"
fi

# ============================================
# Step 2: 初始化 Swarm
# ============================================
echo -e "\n${YELLOW}Step 2: 初始化 Docker Swarm${NC}"

if docker info | grep -q "Swarm: active"; then
    log_info "Swarm 已初始化"
else
    log_info "初始化 Swarm..."
    docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || {
        log_error "Swarm 初始化失败"
        echo "尝试运行: docker swarm init"
        exit 1
    }
    log_info "Swarm 初始化成功"
fi

# ============================================
# Step 3: 创建网络
# ============================================
echo -e "\n${YELLOW}Step 3: 创建 Overlay 网络${NC}"

if docker network inspect autotest-network &> /dev/null; then
    log_info "网络已存在"
else
    docker network create --driver overlay --attachable autotest-network
    log_info "网络创建成功"
fi

# ============================================
# Step 4: 创建 Secrets
# ============================================
echo -e "\n${YELLOW}Step 4: 创建 Docker Secrets${NC}"

SECRETS_DIR="secrets"

# 定义 secrets 映射：(Docker Secret 名称) -> (本地文件名称)
declare -A SECRETS_MAP=(
    ["autotest_postgres_password"]="postgres_password.txt"
    ["autotest_secret_key"]="secret_key.txt"
)

# 可选的 secrets
declare -A OPTIONAL_SECRETS_MAP=(
    ["autotest_smtp_password"]="smtp_password.txt"
    ["autotest_dingtalk_webhook"]="dingtalk_webhook.txt"
    ["autotest_wechat_webhook"]="wechat_webhook.txt"
    ["autotest_oss_access_key"]="oss_access_key.txt"
    ["autotest_oss_secret_key"]="oss_secret_key.txt"
)

# 函数：创建 secret
create_secret_from_file() {
    local secret_name=$1
    local file_name=$2

    # 检查 Docker secret 是否已存在
    if docker secret inspect "$secret_name" &> /dev/null; then
        log_info "Secret '$secret_name' 已存在，跳过"
        return 0
    fi

    # 检查本地文件是否存在
    local file_path="$SECRETS_DIR/$file_name"
    if [ -f "$file_path" ]; then
        # 检查文件是否包含模板值
        if grep -qi "your_" "$file_path" 2>/dev/null; then
            log_error "Secret 文件 '$file_path' 包含模板值，请先修改"
            return 1
        fi

        # 从文件创建 secret
        docker secret create "$secret_name" "$file_path"
        log_info "创建 Secret: $secret_name (来自 $file_path)"
    else
        log_error "Secret 文件不存在: $file_path"
        log_info "请先运行以下命令初始化 secrets 目录:"
        echo "  ./deploy.sh secrets-init"
        echo "  然后编辑 $SECRETS_DIR/*.txt 文件填入真实值"
        return 1
    fi
}

# 函数：创建可选 secret
create_optional_secret() {
    local secret_name=$1
    local file_name=$2

    # 检查 Docker secret 是否已存在
    if docker secret inspect "$secret_name" &> /dev/null; then
        log_info "可选 Secret '$secret_name' 已存在，跳过"
        return 0
    fi

    # 检查本地文件是否存在
    local file_path="$SECRETS_DIR/$file_name"
    if [ -f "$file_path" ]; then
        # 检查文件是否包含模板值
        if grep -qi "your_" "$file_path" 2>/dev/null; then
            log_info "可选 Secret '$file_path' 包含模板值，跳过"
            return 0
        fi

        # 从文件创建 secret
        docker secret create "$secret_name" "$file_path"
        log_info "创建可选 Secret: $secret_name (来自 $file_path)"
    else
        log_info "可选 Secret 文件不存在: $file_path，跳过"
    fi
}

# 创建必需的 secrets
echo -e "${YELLOW}创建必需的 Secrets:${NC}"
for secret_name in "${!SECRETS_MAP[@]}"; do
    file_name="${SECRETS_MAP[$secret_name]}"
    if ! create_secret_from_file "$secret_name" "$file_name"; then
        log_error "创建必需 Secret 失败: $secret_name"
        exit 1
    fi
done

# 创建可选的 secrets
echo -e "\n${YELLOW}创建可选的 Secrets:${NC}"
for secret_name in "${!OPTIONAL_SECRETS_MAP[@]}"; do
    file_name="${OPTIONAL_SECRETS_MAP[$secret_name]}"
    create_optional_secret "$secret_name" "$file_name"
done

# ============================================
# Step 5: 构建镜像
# ============================================
echo -e "\n${YELLOW}Step 5: 构建镜像${NC}"

if [ -f "Dockerfile" ]; then
    log_info "构建 Docker 镜像（可能需要几分钟）..."
    docker build -t autotest-platform:latest .
    log_info "镜像构建成功"
else
    log_error "Dockerfile 不存在"
    exit 1
fi

# ============================================
# Step 6: 部署服务
# ============================================
echo -e "\n${YELLOW}Step 6: 部署服务栈${NC}"

if [ -f "$COMPOSE_FILE" ]; then
    log_info "使用配置文件: $COMPOSE_FILE"
else
    log_error "配置文件不存在: $COMPOSE_FILE"
    exit 1
fi

docker stack deploy -c $COMPOSE_FILE $STACK_NAME
log_info "服务部署命令已执行"

# ============================================
# Step 7: 等待服务启动
# ============================================
echo -e "\n${YELLOW}Step 7: 等待服务启动${NC}"

log_info "等待服务启动（约 60 秒）..."
sleep 10

for i in {1..12}; do
    echo -n "[$i/12] 检查服务状态... "

    # 统计运行中的服务数
    RUNNING=$(docker service ls --filter name=$STACK_NAME --format "{{.Replicas}}" 2>/dev/null | grep -c "1/1" || echo "0")
    TOTAL=$(docker service ls --filter name=$STACK_NAME -q 2>/dev/null | wc -l)

    if [ "$RUNNING" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        echo -e "${GREEN}✓ 所有服务已启动${NC}"
        break
    else
        echo "运行中: $RUNNING/$TOTAL"
        sleep 5
    fi
done

# ============================================
# Step 8: 显示服务状态
# ============================================
echo -e "\n${YELLOW}Step 8: 服务状态${NC}"

docker stack services $STACK_NAME

echo -e "\n${YELLOW}服务任务状态:${NC}"
docker stack ps $STACK_NAME --format "table {{.Name}}\t{{.CurrentState}}\t{{.Error}}"

# ============================================
# Step 9: 检查是否有失败的任务
# ============================================
echo -e "\n${YELLOW}Step 9: 错误检查${NC}"

FAILED=$(docker stack ps $STACK_NAME --filter desired-state=failed -q 2>/dev/null | wc -l)
if [ "$FAILED" -gt 0 ]; then
    log_error "发现 $FAILED 个失败的任务"
    echo -e "\n${YELLOW}失败任务详情:${NC}"
    docker stack ps $STACK_NAME --filter desired-state=failed --no-trunc

    echo -e "\n${YELLOW}查看服务日志:${NC}"
    for svc in api postgres redis; do
        echo "--- $svc 日志 ---"
        docker service logs ${STACK_NAME}_${svc} --tail 20 2>/dev/null
    done
else
    log_info "没有失败的任务"
fi

# ============================================
# Step 10: 访问信息
# ============================================
echo -e "\n${YELLOW}======================================"
echo "部署完成"
echo "======================================${NC}"

echo -e "\n${GREEN}访问地址:${NC}"
echo "  API: http://localhost:5000"
echo "  API 文档: http://localhost:5000/docs"
echo "  健康检查: http://localhost:5000/health"

echo -e "\n${GREEN}常用命令:${NC}"
echo "  查看服务: docker stack services $STACK_NAME"
echo "  查看日志: docker service logs ${STACK_NAME}_api"
echo "  查看任务: docker stack ps $STACK_NAME"
echo "  删除服务: docker stack rm $STACK_NAME"

echo -e "\n${GREEN}故障排查:${NC}"
echo "  运行诊断: ./scripts/diagnose_swarm.sh"
