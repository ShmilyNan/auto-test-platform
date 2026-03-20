#!/bin/bash

# ============================================
# Docker Swarm 部署脚本 - 支持 Secrets 管理
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
STACK_NAME="autotest"
COMPOSE_FILE="docker-stack.yaml"
SECRETS_DIR="secrets"
SECRETS_TEMPLATE_DIR="secrets/.template"

# Secrets 列表
REQUIRED_SECRETS=(
    "postgres_password"
    "secret_key"
)

OPTIONAL_SECRETS=(
    "smtp_password"
    "dingtalk_webhook"
    "wechat_webhook"
    "oss_access_key"
    "oss_secret_key"
)

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# ============================================
# Secrets 管理
# ============================================

# 初始化 secrets 目录
init_secrets_dir() {
    log_info "初始化 Secrets 目录..."

    if [ ! -d "$SECRETS_DIR" ]; then
        mkdir -p "$SECRETS_DIR"
        log_info "创建目录: $SECRETS_DIR"
    fi

    # 复制模板文件
    if [ -d "$SECRETS_TEMPLATE_DIR" ]; then
        for secret_file in "$SECRETS_TEMPLATE_DIR"/*.txt; do
            if [ -f "$secret_file" ]; then
                filename=$(basename "$secret_file")
                target="$SECRETS_DIR/$filename"

                if [ ! -f "$target" ]; then
                    cp "$secret_file" "$target"
                    log_info "复制模板: $filename"
                else
                    log_warn "文件已存在，跳过: $filename"
                fi
            fi
        done
    fi

    log_info "请编辑 $SECRETS_DIR/ 目录下的文件，填入真实值"
}

# 生成随机密钥
generate_secrets() {
    log_info "生成随机 Secrets..."

    # PostgreSQL 密码
    if [ ! -f "$SECRETS_DIR/postgres_password.txt" ] || grep -q "your_secure_postgres_password" "$SECRETS_DIR/postgres_password.txt"; then
        openssl rand -base64 32 > "$SECRETS_DIR/postgres_password.txt"
        log_info "生成: postgres_password"
    fi

    # JWT 密钥
    if [ ! -f "$SECRETS_DIR/secret_key.txt" ] || grep -q "your-super-secret-key" "$SECRETS_DIR/secret_key.txt"; then
        openssl rand -base64 32 > "$SECRETS_DIR/secret_key.txt"
        log_info "生成: secret_key"
    fi

    log_info "Secrets 生成完成"
}

# 创建 Docker Secrets
create_secrets() {
    log_info "创建 Docker Secrets..."

    local created=0
    local skipped=0

    # 创建必需的 secrets
    for secret in "${REQUIRED_SECRETS[@]}"; do
        local secret_file="$SECRETS_DIR/${secret}.txt"
        local secret_name="${STACK_NAME}_${secret}"

        # 检查文件是否存在
        if [ ! -f "$secret_file" ]; then
            log_error "Secret 文件不存在: $secret_file"
            log_info "请先运行: ./deploy.sh secrets-init"
            exit 1
        fi

        # 检查是否包含模板值
        if grep -qi "your_" "$secret_file"; then
            log_error "Secret 文件包含模板值，请先修改: $secret_file"
            exit 1
        fi

        # 检查 Docker secret 是否已存在
        if docker secret inspect "$secret_name" > /dev/null 2>&1; then
            log_warn "Secret 已存在: $secret_name (跳过)"
            ((skipped++))
        else
            # 创建 secret
            docker secret create "$secret_name" "$secret_file"
            log_info "创建 Secret: $secret_name ✓"
            ((created++))
        fi
    done

    # 创建可选的 secrets
    for secret in "${OPTIONAL_SECRETS[@]}"; do
        local secret_file="$SECRETS_DIR/${secret}.txt"
        local secret_name="${STACK_NAME}_${secret}"

        # 检查文件是否存在且不为空
        if [ ! -f "$secret_file" ]; then
            log_debug "可选 Secret 文件不存在，跳过: $secret"
            continue
        fi

        # 检查是否包含模板值
        if grep -qi "your_" "$secret_file"; then
            log_debug "可选 Secret 包含模板值，跳过: $secret"
            continue
        fi

        # 检查 Docker secret 是否已存在
        if docker secret inspect "$secret_name" > /dev/null 2>&1; then
            log_debug "可选 Secret 已存在: $secret_name (跳过)"
        else
            docker secret create "$secret_name" "$secret_file"
            log_info "创建可选 Secret: $secret_name ✓"
        fi
    done

    echo ""
    log_info "Secrets 创建完成: $created 个创建, $skipped 个跳过"
}

# 更新 Secret（先删除再创建）
update_secret() {
    local secret_name=$1

    if [ -z "$secret_name" ]; then
        log_error "请指定 Secret 名称"
        log_info "用法: $0 secrets-update <secret-name>"
        log_info "可用的 Secrets:"
        for s in "${REQUIRED_SECRETS[@]}" "${OPTIONAL_SECRETS[@]}"; do
            echo "  - $s"
        done
        exit 1
    fi

    local secret_file="$SECRETS_DIR/${secret_name}.txt"
    local docker_secret_name="${STACK_NAME}_${secret_name}"

    if [ ! -f "$secret_file" ]; then
        log_error "Secret 文件不存在: $secret_file"
        exit 1
    fi

    # 删除旧的 secret
    if docker secret inspect "$docker_secret_name" > /dev/null 2>&1; then
        log_info "删除旧 Secret: $docker_secret_name"
        docker secret rm "$docker_secret_name"
    fi

    # 创建新的 secret
    docker secret create "$docker_secret_name" "$secret_file"
    log_info "更新 Secret: $docker_secret_name ✓"

    # 提示重启相关服务
    log_warn "Secret 已更新，需要重启相关服务才能生效"
    log_info "运行: ./deploy.sh update api"
}

# 列出所有 Secrets
list_secrets() {
    log_info "Docker Secrets 列表:"
    echo ""

    # 列出所有相关的 secrets
    docker secret ls --filter "name=${STACK_NAME}_" --format "table {{.Name}}\t{{.CreatedAt}}\t{{.UpdatedAt}}"

    echo ""
    log_info "本地 Secret 文件:"
    if [ -d "$SECRETS_DIR" ]; then
        for f in "$SECRETS_DIR"/*.txt; do
            if [ -f "$f" ]; then
                filename=$(basename "$f")
                size=$(wc -c < "$f")
                modified=$(stat -c %y "$f" | cut -d. -f1)
                echo "  - $filename ($size bytes, modified: $modified)"
            fi
        done
    fi
}

# 删除所有 Secrets
remove_secrets() {
    log_warn "即将删除所有 Docker Secrets"
    read -p "确认删除? (y/N): " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        for secret in "${REQUIRED_SECRETS[@]}" "${OPTIONAL_SECRETS[@]}"; do
            local secret_name="${STACK_NAME}_${secret}"
            if docker secret inspect "$secret_name" > /dev/null 2>&1; then
                docker secret rm "$secret_name"
                log_info "删除 Secret: $secret_name"
            fi
        done
        log_info "所有 Secrets 已删除"
    else
        log_info "取消删除"
    fi
}

# ============================================
# Swarm 管理
# ============================================

# 检查Docker Swarm状态
check_swarm() {
    log_info "检查Docker Swarm状态..."
    if ! docker info | grep -q "Swarm: active"; then
        log_error "Docker Swarm未激活，请先初始化Swarm集群"
        log_info "运行: docker swarm init"
        exit 1
    fi
    log_info "Docker Swarm已激活"
}

# 创建必要的目录
create_directories() {
    log_info "创建数据目录..."
    sudo mkdir -p /data/autotest/{postgres,redis,storage,logs,allure-results,allure-report}
    sudo chown -R $(whoami):$(whoami) /data/autotest
    log_info "数据目录创建完成"
}

# 初始化Swarm集群（如果未初始化）
init_swarm() {
    if docker info | grep -q "Swarm: active"; then
        log_info "Swarm已初始化"
    else
        log_info "初始化Swarm集群..."
        docker swarm init
        log_info "Swarm集群初始化完成"
    fi
}

# 创建Overlay网络
create_network() {
    log_info "创建Overlay网络..."
    if ! docker network inspect autotest-network > /dev/null 2>&1; then
        docker network create --driver overlay --attachable autotest-network
        log_info "网络创建完成"
    else
        log_info "网络已存在"
    fi
}

# 构建镜像
build_image() {
    log_info "构建Docker镜像..."
    docker build -t autotest-platform:latest .

    if [ -n "$DOCKER_REGISTRY" ]; then
        log_info "推送镜像到仓库..."
        docker tag autotest-platform:latest ${DOCKER_REGISTRY}/autotest-platform:${IMAGE_TAG:-latest}
        docker push ${DOCKER_REGISTRY}/autotest-platform:${IMAGE_TAG:-latest}
    fi

    log_info "镜像构建完成"
}

# 部署服务
deploy() {
    log_info "部署服务栈: ${STACK_NAME}"

    # 检查必需的 secrets 是否存在
    log_info "检查 Secrets..."
    for secret in "${REQUIRED_SECRETS[@]}"; do
        local secret_name="${STACK_NAME}_${secret}"
        if ! docker secret inspect "$secret_name" > /dev/null 2>&1; then
            log_error "必需的 Secret 不存在: $secret_name"
            log_info "请先运行: ./deploy.sh secrets-create"
            exit 1
        fi
    done
    log_info "Secrets 检查通过 ✓"

    # 部署
    docker stack deploy -c $COMPOSE_FILE $STACK_NAME

    log_info "部署完成，等待服务启动..."
    sleep 10

    # 显示服务状态
    docker stack services $STACK_NAME
}

# 更新服务
update_service() {
    local service_name=$1

    if [ -z "$service_name" ]; then
        log_error "请指定服务名称"
        log_info "用法: $0 update <service-name>"
        log_info "可用服务:"
        docker stack services $STACK_NAME --format "{{.Name}}"
        exit 1
    fi

    log_info "更新服务: ${service_name}"

    # 强制更新
    docker service update --force ${STACK_NAME}_${service_name}

    log_info "服务更新完成"
}

# 回滚服务
rollback_service() {
    local service_name=$1

    if [ -z "$service_name" ]; then
        log_error "请指定服务名称"
        log_info "用法: $0 rollback <service-name>"
        exit 1
    fi

    log_info "回滚服务: ${service_name}"
    docker service rollback ${STACK_NAME}_${service_name}
    log_info "服务回滚完成"
}

# 扩缩容服务
scale_service() {
    local service_name=$1
    local replicas=$2

    if [ -z "$service_name" ] || [ -z "$replicas" ]; then
        log_error "请指定服务名称和副本数"
        log_info "用法: $0 scale <service-name> <replicas>"
        exit 1
    fi

    log_info "扩缩容服务: ${service_name} -> ${replicas} 副本"
    docker service scale ${STACK_NAME}_${service_name}=${replicas}
    log_info "扩缩容完成"
}

# 查看服务日志
logs() {
    local service_name=$1

    if [ -z "$service_name" ]; then
        service_name="api"
    fi

    log_info "查看服务日志: ${service_name}"
    docker service logs -f ${STACK_NAME}_${service_name}
}

# 查看服务状态
status() {
    log_info "服务状态:"
    docker stack services $STACK_NAME

    echo ""
    log_info "服务详情:"
    docker stack ps $STACK_NAME
}

# 删除服务栈
remove() {
    log_warn "即将删除服务栈: ${STACK_NAME}"
    read -p "确认删除? (y/N): " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker stack rm $STACK_NAME
        log_info "服务栈已删除"
    else
        log_info "取消删除"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    local services=("api" "celery-worker" "celery-beat")

    for service in "${services[@]}"; do
        local running=$(docker service ps ${STACK_NAME}_${service} --filter "desired-state=running" -q 2>/dev/null | wc -l)
        local desired=$(docker service inspect ${STACK_NAME}_${service} --format '{{.Spec.Mode.Replicated.Replicas}}' 2>/dev/null || echo "0")

        if [ "$running" -eq "$desired" ] && [ "$desired" -gt 0 ]; then
            log_info "${service}: ${running}/${desired} ✓"
        else
            log_warn "${service}: ${running}/${desired} ✗"
        fi
    done
}

# 帮助信息
help() {
    echo "Docker Swarm 部署脚本 - 支持 Secrets 管理"
    echo ""
    echo "用法: $0 <command> [arguments]"
    echo ""
    echo "Secrets 管理:"
    echo "  secrets-init          初始化 Secrets 目录（复制模板）"
    echo "  secrets-generate      生成随机 Secrets（postgres_password, secret_key）"
    echo "  secrets-create        创建 Docker Secrets"
    echo "  secrets-update <name> 更新指定的 Secret"
    echo "  secrets-list          列出所有 Secrets"
    echo "  secrets-remove        删除所有 Docker Secrets"
    echo ""
    echo "服务管理:"
    echo "  init                  初始化Swarm集群"
    echo "  deploy                部署服务栈（自动检查 Secrets）"
    echo "  update <svc>          更新指定服务"
    echo "  rollback <svc>        回滚指定服务"
    echo "  scale <svc> <n>       扩缩容服务"
    echo "  logs [svc]            查看服务日志"
    echo "  status                查看服务状态"
    echo "  health                健康检查"
    echo "  remove                删除服务栈"
    echo "  build                 构建镜像"
    echo ""
    echo "帮助:"
    echo "  help                  显示帮助信息"
    echo ""
    echo "示例:"
    echo "  # 完整部署流程"
    echo "  $0 init"
    echo "  $0 secrets-init"
    echo "  $0 secrets-generate  # 或手动编辑 secrets/*.txt"
    echo "  $0 secrets-create"
    echo "  $0 deploy"
    echo ""
    echo "  # 更新 Secret 并重启服务"
    echo "  $0 secrets-update postgres_password"
    echo "  $0 update api"
}

# 主函数
main() {
    local command=$1
    shift

    case $command in
        secrets-init)
            init_secrets_dir
            ;;
        secrets-generate)
            generate_secrets
            ;;
        secrets-create)
            create_secrets
            ;;
        secrets-update)
            update_secret $@
            ;;
        secrets-list)
            list_secrets
            ;;
        secrets-remove)
            remove_secrets
            ;;
        init)
            init_swarm
            create_directories
            create_network
            ;;
        deploy)
            check_swarm
            deploy
            ;;
        update)
            update_service $@
            ;;
        rollback)
            rollback_service $@
            ;;
        scale)
            scale_service $@
            ;;
        logs)
            logs $@
            ;;
        status)
            status
            ;;
        health)
            health_check
            ;;
        remove)
            remove
            ;;
        build)
            build_image
            ;;
        help|--help|-h)
            help
            ;;
        *)
            log_error "未知命令: $command"
            help
            exit 1
            ;;
    esac
}

main "$@"
