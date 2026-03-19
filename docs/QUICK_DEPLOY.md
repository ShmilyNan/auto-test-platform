# 🚀 快速部署指南（使用 Docker Secrets）

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4核 CPU, 8GB 内存

## 一键部署（推荐）

```bash
# 1. 初始化 Swarm
./deploy.sh init

# 2. 初始化 Secrets 目录
./deploy.sh secrets-init

# 3. 生成随机密钥（或手动编辑 secrets/*.txt）
./deploy.sh secrets-generate

# 4. 创建 Docker Secrets
./deploy.sh secrets-create

# 5. 部署服务
./deploy.sh deploy

# 6. 验证部署
./deploy.sh status
```

## Secrets 管理

### 必需的 Secrets

| Secret 名称 | 说明 | 用途 |
|-------------|------|------|
| `postgres_password` | PostgreSQL 密码 | 数据库认证 |
| `secret_key` | JWT 密钥 | Token 加密 |

### 可选的 Secrets

| Secret 名称 | 说明 | 用途 |
|-------------|------|------|
| `smtp_password` | SMTP 密码 | 邮件通知 |
| `dingtalk_webhook` | 钉钉 Webhook | 钉钉通知 |
| `wechat_webhook` | 微信 Webhook | 微信通知 |
| `oss_access_key` | OSS 访问密钥 | 对象存储 |
| `oss_secret_key` | OSS 密钥 | 对象存储 |

### Secrets 命令

```bash
# 初始化 Secrets 目录
./deploy.sh secrets-init

# 生成随机密钥
./deploy.sh secrets-generate

# 创建 Docker Secrets
./deploy.sh secrets-create

# 查看 Secrets 列表
./deploy.sh secrets-list

# 更新 Secret
./deploy.sh secrets-update <name>

# 删除所有 Secrets
./deploy.sh secrets-remove
```

## 手动部署

### 1. 初始化 Swarm

```bash
# 主节点
docker swarm init --advertise-addr <MANAGER-IP>

# Worker节点加入
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

### 2. 创建数据目录

```bash
sudo mkdir -p /data/autotest/{postgres,redis,storage,logs}
sudo chown -R $(whoami):$(whoami) /data/autotest
```

### 3. 配置 Secrets

```bash
# 创建 secrets 目录
mkdir -p secrets

# 生成密钥
openssl rand -base64 32 > secrets/postgres_password.txt
openssl rand -base64 32 > secrets/secret_key.txt

# 创建 Docker Secrets
docker secret create autotest_postgres_password secrets/postgres_password.txt
docker secret create autotest_secret_key secrets/secret_key.txt
```

### 4. 部署服务

```bash
docker stack deploy -c docker-stack.yml autotest
```

### 5. 查看服务

```bash
docker stack services autotest
docker stack ps autotest
```

## 服务管理

```bash
# 查看状态
./deploy.sh status

# 查看日志
./deploy.sh logs api

# 更新服务
./deploy.sh update api

# 扩缩容
./deploy.sh scale api 3

# 健康检查
./deploy.sh health
```

## 访问地址

- **API**: http://localhost
- **API文档**: http://localhost/docs
- **健康检查**: http://localhost/health
- **Swarm监控**: http://localhost:8080 (可选)

## 安全配置

### 1. 确保 Secrets 不被提交

```bash
# 检查 .gitignore
grep -q "secrets/*.txt" .gitignore || echo "secrets/*.txt" >> .gitignore
```

### 2. 设置文件权限

```bash
chmod 600 secrets/*.txt
```

### 3. 定期轮换密钥

```bash
# 生成新密钥
openssl rand -base64 32 > secrets/secret_key.txt

# 更新 Docker Secret
./deploy.sh secrets-update secret_key

# 重启服务
./deploy.sh update api
```

## 故障排查

### 检查 Secrets 是否存在

```bash
docker secret ls
```

### 检查容器内的 Secrets

```bash
docker exec -it <container-id> ls -la /run/secrets/
```

### 查看服务日志

```bash
docker service logs -f autotest_api
```

## 完整文档

详细的部署和 Secrets 管理文档请参考：
- [Docker Secrets 管理指南](docs/docker_secrets_guide.md)
- [Docker Swarm 部署指南](docs/deployment_swarm.md)
- [项目架构文档](docs/architecture.md)

## 注意事项

1. **生产环境**必须使用强密码和密钥
2. **Secrets 文件**不要提交到 Git
3. **定期轮换**敏感信息（建议 90 天）
4. **备份 Secrets**到安全位置
