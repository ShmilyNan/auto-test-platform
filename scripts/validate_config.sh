#!/bin/bash

# ============================================
# 配置验证脚本 - 支持 Secrets 验证
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_debug() { echo -e "${BLUE}[i]${NC} $1"; }

errors=0
warnings=0

echo "======================================"
echo "配置验证（支持 Docker Secrets）"
echo "======================================"
echo ""

# 1. 检查必要文件
echo "1. 检查必要文件..."
files=(
    "docker-stack.yml"
    "Dockerfile"
    ".dockerignore"
    "nginx/nginx.conf"
    "deploy.sh"
    "requirements.txt"
    "main.py"
    "core/config.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        log_info "$file 存在"
    else
        log_error "$file 不存在"
        ((errors++))
    fi
done

echo ""

# 2. 检查 Secrets 配置
echo "2. 检查 Secrets 配置..."

# 检查 secrets 目录
if [ -d "secrets" ]; then
    log_info "secrets 目录存在"

    # 检查模板目录
    if [ -d "secrets/.template" ]; then
        log_info "secrets/.template 目录存在"
    else
        log_warn "secrets/.template 目录不存在"
        ((warnings++))
    fi

    # 检查 README
    if [ -f "secrets/README.md" ]; then
        log_info "secrets/README.md 存在"
    else
        log_warn "secrets/README.md 不存在"
        ((warnings++))
    fi
else
    log_warn "secrets 目录不存在，运行 ./deploy.sh secrets-init 创建"
    ((warnings++))
fi

# 检查必需的 secrets 文件
required_secrets=(
    "secrets/postgres_password.txt"
    "secrets/secret_key.txt"
)

for secret_file in "${required_secrets[@]}"; do
    if [ -f "$secret_file" ]; then
        # 检查是否包含模板值
        if grep -qi "your_" "$secret_file"; then
            log_error "$secret_file 包含模板值，请修改"
            ((errors++))
        else
            log_info "$secret_file 已配置"
        fi
    else
        log_warn "$secret_file 不存在（运行 ./deploy.sh secrets-init）"
        ((warnings++))
    fi
done

# 检查可选的 secrets 文件
optional_secrets=(
    "secrets/smtp_password.txt"
    "secrets/dingtalk_webhook.txt"
    "secrets/wechat_webhook.txt"
    "secrets/oss_access_key.txt"
    "secrets/oss_secret_key.txt"
)

for secret_file in "${optional_secrets[@]}"; do
    if [ -f "$secret_file" ]; then
        if grep -qi "your_" "$secret_file"; then
            log_debug "$secret_file 包含模板值（可选，可忽略）"
        else
            log_info "$secret_file 已配置"
        fi
    fi
done

echo ""

# 3. 检查 Docker Secrets（如果 Docker 可用）
echo "3. 检查 Docker Secrets..."
if command -v docker &> /dev/null; then
    if docker info 2>/dev/null | grep -q "Swarm: active"; then
        log_info "Docker Swarm 已激活"

        # 检查必需的 Docker Secrets
        docker_secrets=(
            "autotest_postgres_password"
            "autotest_secret_key"
        )

        for secret_name in "${docker_secrets[@]}"; do
            if docker secret inspect "$secret_name" > /dev/null 2>&1; then
                log_info "Docker Secret 存在: $secret_name"
            else
                log_warn "Docker Secret 不存在: $secret_name（运行 ./deploy.sh secrets-create）"
                ((warnings++))
            fi
        done
    else
        log_warn "Docker Swarm 未激活"
        log_debug "运行 docker swarm init 初始化"
    fi
else
    log_warn "Docker 未安装，跳过 Docker Secrets 检查"
fi

echo ""

# 4. 检查 docker-stack.yml 配置
echo "4. 检查 docker-stack.yml 配置..."
if [ -f "docker-stack.yml" ]; then
    # 检查 secrets 定义
    if grep -q "secrets:" docker-stack.yml; then
        log_info "docker-stack.yml 包含 secrets 定义"
    else
        log_error "docker-stack.yml 缺少 secrets 定义"
        ((errors++))
    fi

    # 检查服务是否引用 secrets
    if grep -q "secrets:" docker-stack.yml && grep -A 5 "api:" docker-stack.yml | grep -q "secrets:"; then
        log_info "api 服务引用了 secrets"
    else
        log_warn "api 服务可能未引用 secrets"
        ((warnings++))
    fi

    # 检查环境变量是否使用 _FILE 后缀
    if grep -q "_FILE:" docker-stack.yml; then
        log_info "docker-stack.yml 使用 _FILE 环境变量"
    else
        log_warn "docker-stack.yml 可能未使用 _FILE 环境变量"
        ((warnings++))
    fi
fi

echo ""

# 5. 检查配置文件是否支持 Secrets
echo "5. 检查应用配置..."
if [ -f "core/config.py" ]; then
    # 检查是否包含 read_secret 函数
    if grep -q "def read_secret" core/config.py; then
        log_info "core/config.py 包含 read_secret 函数"
    else
        log_error "core/config.py 缺少 read_secret 函数"
        ((errors++))
    fi

    # 检查是否读取 /run/secrets/
    if grep -q "/run/secrets/" core/config.py; then
        log_info "core/config.py 支持读取 Docker Secrets"
    else
        log_error "core/config.py 不支持读取 Docker Secrets"
        ((errors++))
    fi

    # 检查是否包含 _load_secrets 方法
    if grep -q "_load_secrets" core/config.py; then
        log_info "core/config.py 包含 _load_secrets 方法"
    else
        log_error "core/config.py 缺少 _load_secrets 方法"
        ((errors++))
    fi
fi

echo ""

# 6. 检查 .gitignore
echo "6. 检查 .gitignore..."
if [ -f ".gitignore" ]; then
    if grep -q "secrets/\*\.txt" .gitignore; then
        log_info ".gitignore 包含 secrets/*.txt"
    else
        log_error ".gitignore 缺少 secrets/*.txt（可能泄露敏感信息）"
        ((errors++))
    fi

    # 检查是否排除了模板
    if grep -q "!secrets/\.template/" .gitignore || grep -q "secrets/\*\.txt" .gitignore; then
        log_info ".gitignore 正确配置"
    else
        log_warn ".gitignore 可能不完整"
        ((warnings++))
    fi
else
    log_error ".gitignore 不存在"
    ((errors++))
fi

echo ""

# 7. 检查文件权限
echo "7. 检查文件权限..."
if [ -d "secrets" ]; then
    for secret_file in secrets/*.txt; do
        if [ -f "$secret_file" ]; then
            perms=$(stat -c %a "$secret_file" 2>/dev/null || stat -f %OLp "$secret_file" 2>/dev/null)
            if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
                log_info "$secret_file 权限正确 ($perms)"
            else
                log_warn "$secret_file 权限过于宽松 ($perms)，建议设置为 600"
                ((warnings++))
            fi
        fi
    done
fi

echo ""

# 8. 检查部署脚本
echo "8. 检查部署脚本..."
if [ -f "deploy.sh" ]; then
    if [ -x "deploy.sh" ]; then
        log_info "deploy.sh 有执行权限"
    else
        log_warn "deploy.sh 没有执行权限，运行: chmod +x deploy.sh"
        ((warnings++))
    fi

    # 检查 secrets 相关函数
    secret_functions=(
        "secrets-init"
        "secrets-create"
        "secrets-update"
        "secrets-list"
    )

    for func in "${secret_functions[@]}"; do
        if grep -q "$func)" deploy.sh; then
            log_info "deploy.sh 包含 $func 命令"
        else
            log_warn "deploy.sh 缺少 $func 命令"
            ((warnings++))
        fi
    done
fi

echo ""

# 9. 检查文档
echo "9. 检查文档..."
docs=(
    "docs/docker_secrets_guide.md"
    "docs/QUICK_DEPLOY.md"
    "README_DOCKER.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        log_info "$doc 存在"
    else
        log_warn "$doc 不存在"
        ((warnings++))
    fi
done

echo ""

# 10. 端口检查
echo "10. 端口检查..."
required_ports=(80 443 5000)
for port in "${required_ports[@]}"; do
    if ss -tuln 2>/dev/null | grep -q ":${port} "; then
        log_warn "端口 $port 已被占用"
    else
        log_info "端口 $port 可用"
    fi
done

echo ""

# 总结
echo "======================================"
echo "验证结果"
echo "======================================"
echo ""
echo -e "错误: ${RED}${errors}${NC} 个"
echo -e "警告: ${YELLOW}${warnings}${NC} 个"
echo ""

if [ $errors -eq 0 ]; then
    log_info "所有必要检查通过！"
    echo ""
    echo "下一步："
    echo "  1. 编辑 secrets/*.txt 文件，填入真实值"
    echo "  2. 运行 ./deploy.sh secrets-create 创建 Docker Secrets"
    echo "  3. 运行 ./deploy.sh deploy 部署服务"
    echo ""
    exit 0
else
    log_error "发现 $errors 个错误，请修复后再部署"
    exit 1
fi
