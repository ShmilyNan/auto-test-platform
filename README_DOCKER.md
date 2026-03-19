# Docker Swarm 部署配置（支持 Secrets）

本目录包含完整的Docker Swarm部署配置，使用 Docker Secrets 管理敏感信息，支持高可用、可扩展的生产环境部署。

## 📁 文件说明

```
.
├── docker-stack.yml       # Swarm编排配置（使用 Secrets）
├── Dockerfile            # 多阶段构建镜像
├── .dockerignore         # Docker构建忽略文件
├── deploy.sh             # 部署管理脚本（支持 Secrets）
├── secrets/              # Secrets 文件目录
│   ├── .template/        # Secrets 模板
│   └── README.md         # Secrets 使用说明
├── scripts/
│   └── validate_config.sh # 配置验证脚本
├── nginx/
│   └── nginx.conf        # Nginx反向代理配置
└── docs/
    ├── docker_secrets_guide.md # Secrets 详细指南
    ├── deployment_swarm.md     # 详细部署文档
    └── QUICK_DEPLOY.md         # 快速部署指南
```

## 🔐 敏感信息管理

### 为什么使用 Docker Secrets？

| 特性 | Docker Secrets | 环境变量 |
|------|----------------|----------|
| 存储方式 | Raft Log（加密） | 明文环境变量 |
| 可见性 | 仅挂载的容器 | 所有进程可见 |
| 安全性 | 高 | 低 |
| 审计日志 | 有 | 无 |
| 适用环境 | 生产环境 | 开发环境 |

### 管理的 Secrets

#### 必需的 Secrets
- `postgres_password` - PostgreSQL 数据库密码
- `secret_key` - JWT 加密密钥

#### 可选的 Secrets
- `smtp_password` - SMTP 邮件密码
- `dingtalk_webhook` - 钉钉机器人 Webhook
- `wechat_webhook` - 企业微信机器人 Webhook
- `oss_access_key` - OSS 访问密钥
- `oss_secret_key` - OSS 密钥

## 🚀 快速开始

### 1. 初始化 Swarm 集群

```bash
./deploy.sh init
```

### 2. 配置 Secrets

```bash
# 初始化 Secrets 目录
./deploy.sh secrets-init

# 生成随机密钥
./deploy.sh secrets-generate

# 或手动编辑
vim secrets/postgres_password.txt
vim secrets/secret_key.txt
```

### 3. 创建 Docker Secrets

```bash
./deploy.sh secrets-create
```

### 4. 部署服务

```bash
./deploy.sh deploy
```

### 5. 验证部署

```bash
./deploy.sh status
./deploy.sh health
```

## 🔧 Secrets 管理命令

```bash
# 初始化 Secrets 目录
./deploy.sh secrets-init

# 生成随机密钥（postgres_password, secret_key）
./deploy.sh secrets-generate

# 创建 Docker Secrets
./deploy.sh secrets-create

# 查看 Secrets 列表
./deploy.sh secrets-list

# 更新指定的 Secret
./deploy.sh secrets-update <name>

# 删除所有 Docker Secrets
./deploy.sh secrets-remove
```

## 📊 服务架构

```
                    ┌─────────┐
                    │  Nginx  │ :80/:443
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │   API   │ :5000 (x2副本)
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │PostgreSQL│    │  Redis  │    │ Celery  │
    │   :5432  │    │  :6379  │    │ Worker  │
    └──────────┘    └─────────┘    └─────────┘
                                          │
                                     ┌────┴────┐
                                     │  Beat   │
                                     │Scheduler│
                                     └─────────┘
```

### Secrets 在架构中的流转

```
secrets/*.txt              Docker Swarm
     │                          │
     │ docker secret create     │
     ▼                          ▼
┌─────────────┐          ┌─────────────┐
│ autotest_   │          │   Raft Log  │
│ postgres_   │─────────▶│  (加密存储)  │
│ password    │          └─────────────┘
└─────────────┘                │
                               │ 挂载到容器
                               ▼
                         /run/secrets/
                         postgres_password
```

## 📋 配置优先级

配置加载顺序：

1. **Docker Secrets** - `/run/secrets/<secret_name>`
2. **环境变量** - `POSTGRES_PASSWORD`, `SECRET_KEY` 等
3. **.env 文件** - 本地开发环境
4. **config.yaml** - YAML 配置文件
5. **默认值** - 代码中的默认值

## 🛠️ 服务管理

### 服务操作

```bash
# 查看服务状态
./deploy.sh status

# 查看服务日志
./deploy.sh logs api

# 更新服务
./deploy.sh update api

# 扩缩容
./deploy.sh scale api 3

# 健康检查
./deploy.sh health

# 回滚服务
./deploy.sh rollback api

# 删除服务栈
./deploy.sh remove
```

### 手动操作

```bash
# 查看所有服务
docker stack services autotest

# 查看服务任务
docker stack ps autotest

# 查看服务日志
docker service logs -f autotest_api

# 进入容器
docker exec -it <container-id> bash

# 检查容器内的 Secrets
docker exec -it <container-id> ls -la /run/secrets/
```

## 🔒 安全最佳实践

### 1. Secrets 文件管理

```bash
# 设置严格的文件权限
chmod 600 secrets/*.txt

# 确保 .gitignore 包含
echo "secrets/*.txt" >> .gitignore
echo "!secrets/.template/" >> .gitignore
```

### 2. 定期轮换密钥

```bash
# 每 90 天轮换一次
# 1. 生成新密钥
openssl rand -base64 32 > secrets/secret_key.txt

# 2. 更新 Docker Secret
./deploy.sh secrets-update secret_key

# 3. 重启服务
./deploy.sh update api
```

### 3. 配置 HTTPS

```bash
# 使用 Let's Encrypt
certbot certonly --standalone -d yourdomain.com

# 复制证书
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## 📈 监控与日志

### 查看日志

```bash
# API服务日志
docker service logs -f autotest_api --tail 100

# Celery Worker日志
docker service logs -f autotest_celery-worker --tail 100

# 应用日志（容器内）
docker exec -it $(docker ps -q -f name=autotest_api) tail -f /app/logs/app.log
```

### 监控服务

```bash
# 实时监控服务状态
watch -n 1 'docker stack services autotest'

# 查看资源使用
docker stats $(docker ps -q)

# 健康检查
curl http://localhost/health
```

## 🔄 升级与回滚

### 滚动升级

```bash
# 1. 构建新镜像
docker build -t registry.example.com/autotest-platform:v1.1.0 .
docker push registry.example.com/autotest-platform:v1.1.0

# 2. 更新服务
docker service update \
  --image registry.example.com/autotest-platform:v1.1.0 \
  autotest_api

# 3. 验证升级
docker service ps autotest_api
```

### 回滚操作

```bash
# 使用部署脚本
./deploy.sh rollback api

# 或手动回滚
docker service rollback autotest_api
```

## 🐛 故障排查

### Secret 未被读取

```bash
# 1. 检查 Secret 是否存在
docker secret inspect autotest_postgres_password

# 2. 检查容器内的 Secrets
docker exec -it $(docker ps -q -f name=autotest_api) ls -la /run/secrets/

# 3. 读取 Secret 内容
docker exec -it $(docker ps -q -f name=autotest_api) cat /run/secrets/postgres_password
```

### 服务启动失败

```bash
# 查看服务状态
docker service ps autotest_api --no-trunc

# 查看错误日志
docker service logs autotest_api --tail 50

# 检查 Secrets
./deploy.sh secrets-list
```

### Secret 更新后未生效

```bash
# 重启服务
./deploy.sh update api
```

## 💾 备份与恢复

### 备份 Secrets

```bash
# 加密备份
tar -czf - secrets/ | gpg --symmetric --cipher-algo AES256 -o secrets_backup.tar.gz.gpg

# 解密恢复
gpg -d secrets_backup.tar.gz.gpg | tar -xzf -
```

### 备份数据

```bash
# 备份数据库
docker exec $(docker ps -q -f name=autotest_postgres) \
  pg_dump -U autotest_user autotest_platform > backup_$(date +%Y%m%d).sql

# 备份Redis
docker exec $(docker ps -q -f name=autotest_redis) redis-cli BGSAVE
docker cp $(docker ps -q -f name=autotest_redis):/data/dump.rdb redis_backup.rdb
```

## 📚 完整文档

- [Docker Secrets 详细指南](docs/docker_secrets_guide.md)
- [快速部署指南](docs/QUICK_DEPLOY.md)
- [详细部署文档](docs/deployment_swarm.md)
- [项目架构文档](docs/architecture.md)

## ⚠️ 注意事项

1. **生产环境必须使用 Docker Secrets**，不要使用环境变量
2. **Secrets 文件不要提交到 Git**
3. **定期轮换敏感信息**（建议 90 天）
4. **备份 Secrets 到安全位置**
5. **设置严格的文件权限** (chmod 600)
6. **监控服务健康状态**

## 🆘 技术支持

如有问题，请检查：
1. Secrets 状态：`./deploy.sh secrets-list`
2. 服务日志：`docker service logs autotest_api`
3. 容器内 Secrets：`docker exec -it <container-id> ls -la /run/secrets/`
4. 健康状态：`./deploy.sh health`
5. 配置验证：`./scripts/validate_config.sh`
