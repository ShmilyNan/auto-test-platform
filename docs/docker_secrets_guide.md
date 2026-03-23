# Docker Secrets 敏感信息管理指南

## 概述

Docker Secrets 是 Docker Swarm 模式下用于安全管理敏感信息的机制。本项目使用 Secrets 管理以下敏感信息：

### 必需的 Secrets
- `postgres_password` - PostgreSQL 数据库密码
- `secret_key` - JWT 加密密钥

### 可选的 Secrets
- `smtp_password` - SMTP 邮件密码
- `dingtalk_webhook` - 钉钉机器人 Webhook
- `wechat_webhook` - 企业微信机器人 Webhook
- `oss_access_key` - OSS 访问密钥
- `oss_secret_key` - OSS 密钥

## 工作原理

```
┌─────────────────┐
│  secrets/*.txt  │  本地文件（填入真实值）
└────────┬────────┘
         │ docker secret create
         ▼
┌─────────────────┐
│  Docker Secret  │  Swarm 集群加密存储
│  (Raft Log)     │
└────────┬────────┘
         │ 挂载到容器
         ▼
┌─────────────────┐
│  /run/secrets/  │  容器内路径
│  <secret_name>  │
└────────┬────────┘
         │ 应用读取
         ▼
┌─────────────────┐
│   Settings      │  Python 配置对象
└─────────────────┘
```

## 快速开始

### 1. 初始化 Secrets 目录

```bash
./deploy.sh secrets-init
```

这会在 `secrets/` 目录下创建模板文件。

### 2. 生成随机密钥（可选）

```bash
# 自动生成 postgres_password 和 secret_key
./deploy.sh secrets-generate
```

或手动编辑：

```bash
# 生成强密码
openssl rand -base64 32 > secrets/postgres_password.txt
openssl rand -base64 32 > secrets/secret_key.txt

# 编辑可选的 secrets
vim secrets/smtp_password.txt
vim secrets/dingtalk_webhook.txt
```

### 3. 创建 Docker Secrets

```bash
./deploy.sh secrets-create
```

输出示例：
```
[INFO] 创建 Docker Secrets...
[INFO] 创建 Secret: autotest_postgres_password ✓
[INFO] 创建 Secret: autotest_secret_key ✓
[INFO] Secrets 创建完成: 2 个创建, 0 个跳过
```

### 4. 部署服务

```bash
./deploy.sh init
./deploy.sh deploy
```

## 详细用法

### 查看 Secrets 列表

```bash
./deploy.sh secrets-list
```

输出：
```
[INFO] Docker Secrets 列表:

NAME                      CREATED              UPDATED
autotest_postgres_password  2024-01-15 10:00:00  2024-01-15 10:00:00
autotest_secret_key         2024-01-15 10:00:00  2024-01-15 10:00:00

[INFO] 本地 Secret 文件:
  - postgres_password.txt (44 bytes, modified: 2024-01-15 10:00:00)
  - secret_key.txt (44 bytes, modified: 2024-01-15 10:00:00)
```

### 更新 Secret

```bash
# 1. 修改本地文件
vim secrets/postgres_password.txt

# 2. 更新 Docker Secret
./deploy.sh secrets-update postgres_password

# 3. 重启相关服务
./deploy.sh update api
./deploy.sh update celery-worker
```

### 删除所有 Secrets

```bash
./deploy.sh secrets-remove
```

⚠️ **警告**：删除 Secrets 后，需要重新创建才能部署服务。

## 配置优先级

配置加载的优先级如下：

1. **Docker Secrets** - `/run/secrets/<secret_name>`
2. **环境变量** - `DATABASE_URL`, `SECRET_KEY` 等
3. **.env 文件** - 本地开发环境
4. **config.yaml** - YAML 配置文件
5. **默认值** - 代码中的默认值

### 代码实现

```python
# core/config.py
def read_secret(secret_name: str) -> Optional[str]:
    """从 Docker Secrets 文件读取敏感信息"""
    secret_path = Path(f"/run/secrets/{secret_name}")
    
    if secret_path.exists():
        return secret_path.read_text().strip()
    
    return None

class Settings(BaseSettings):
    def _load_secrets(self):
        """从 Docker Secrets 加载敏感信息"""
        # PostgreSQL 密码
        self._postgres_password = read_secret("postgres_password")
        if self._postgres_password:
            self.POSTGRES_PASSWORD = self._postgres_password
        
        # JWT 密钥
        self._secret_key = read_secret("secret_key")
        if self._secret_key:
            self.SECRET_KEY = self._secret_key
```

## Docker Compose 配置

### docker-stack.yml

```yaml
version: '3.8'

secrets:
  postgres_password:
    external: true
    name: autotest_postgres_password
  
  secret_key:
    external: true
    name: autotest_secret_key

services:
  api:
    secrets:
      - postgres_password
      - secret_key
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
      - SECRET_KEY_FILE=/run/secrets/secret_key
```

### PostgreSQL 服务

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_USER: autotest_user
    POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    POSTGRES_DB: autotest_platform
  secrets:
    - postgres_password
```

## 安全最佳实践

### 1. 文件权限

```bash
# 设置严格的文件权限
chmod 600 secrets/*.txt
```

### 2. Git 忽略

确保 `.gitignore` 包含：

```gitignore
# Secrets
secrets/*.txt
!secrets/.template/
!secrets/README.md
```

### 3. 定期轮换

建议定期轮换敏感信息：

```bash
# 每 90 天轮换一次
# 1. 生成新密钥
openssl rand -base64 32 > secrets/secret_key.txt

# 2. 更新 Docker Secret
./deploy.sh secrets-update secret_key

# 3. 滚动更新服务
./deploy.sh update api
```

### 4. 审计日志

查看 Secrets 访问记录：

```bash
# 查看 Swarm 服务日志
docker service logs autotest_api | grep -i secret

# 查看应用日志
docker exec -it $(docker ps -q -f name=autotest_api) \
    tail -f /app/logs/app.log | grep -i secret
```

## 故障排查

### Secret 未被读取

**症状**：服务启动失败，提示数据库连接错误

**排查**：

```bash
# 1. 检查 Secret 是否存在
docker secret inspect autotest_postgres_password

# 2. 检查服务是否挂载了 Secret
docker service inspect autotest_api --format '{{json .Spec.TaskTemplate.ContainerSpec.Secrets}}'

# 3. 进入容器检查
docker exec -it $(docker ps -q -f name=autotest_api) ls -la /run/secrets/

# 4. 读取 Secret 内容
docker exec -it $(docker ps -q -f name=autotest_api) cat /run/secrets/postgres_password
```

### Secret 更新后未生效

**原因**：服务需要重启才能读取新的 Secret

**解决**：

```bash
./deploy.sh update api
```

### 权限问题

**症状**：无法读取 Secret 文件

**解决**：

```bash
# 检查容器内权限
docker exec -it $(docker ps -q -f name=autotest_api) ls -la /run/secrets/

# Secrets 默认权限为 444 (只读)
```

## 开发环境

在开发环境中，可以不使用 Docker Secrets，直接使用环境变量：

### 方式一：使用 .env 文件

```bash
# .env.dev
POSTGRES_PASSWORD=your_password
SECRET_KEY=your_secret_key
```

### 方式二：使用环境变量

```bash
export POSTGRES_PASSWORD=your_password
export SECRET_KEY=your_secret_key
```

应用会自动检测：如果 Docker Secrets 不存在，则从环境变量读取。

## 迁移指南

### 从环境变量迁移到 Secrets

1. **导出现有环境变量**

```bash
# 从 .env.dev 文件提取敏感信息
grep -E "PASSWORD|SECRET|KEY|TOKEN" .env.dev > secrets_extract.txt
```

2. **创建 Secrets 文件**

```bash
# 手动创建每个 secret 文件
echo "your_postgres_password" > secrets/postgres_password.txt
echo "your_jwt_secret_key" > secrets/secret_key.txt
```

3. **创建 Docker Secrets**

```bash
./deploy.sh secrets-create
```

4. **更新 docker-stack.yml**

确保所有服务都引用了 Secrets。

5. **重新部署**

```bash
./deploy.sh remove
./deploy.sh deploy
```

## 参考资料

- [Docker Secrets 官方文档](https://docs.docker.com/engine/swarm/secrets/)
- [Docker Secrets 最佳实践](https://docs.docker.com/engine/swarm/secrets/#best-practices)
- [在 Python 中使用 Docker Secrets](https://docs.docker.com/engine/swarm/secrets/#use-secrets-in-python)

## 常见问题

### Q: Secrets 和环境变量有什么区别？

| 特性 | Secrets | 环境变量 |
|------|---------|----------|
| 存储位置 | Raft Log（加密） | 明文环境变量 |
| 可见性 | 仅挂载的容器 | 所有进程可见 |
| 更新方式 | 需要重启服务 | 立即生效 |
| 审计日志 | 有 | 无 |
| 大小限制 | 500KB | 无限制 |

### Q: 可以在 docker-compose.yml 中使用 Secrets 吗？

可以，但需要使用 Docker Swarm 模式：

```bash
# 启用 Swarm
docker swarm init

# 使用 stack 部署
docker stack deploy -c docker-compose.yml autotest
```

### Q: 如何备份 Secrets？

Docker Secrets 存储在 Raft Log 中，建议：

1. **保存原始文件**：备份 `secrets/*.txt` 文件到安全位置
2. **使用加密存储**：使用 GPG 或 Vault 加密备份

```bash
# 加密备份
tar -czf - secrets/ | gpg --symmetric --cipher-algo AES256 -o secrets_backup.tar.gz.gpg

# 解密恢复
gpg -d secrets_backup.tar.gz.gpg | tar -xzf -
```

### Q: 多个服务可以共享同一个 Secret 吗？

可以。在 `docker-stack.yml` 中声明一次，多个服务都可以引用：

```yaml
secrets:
  postgres_password:
    external: true

services:
  api:
    secrets:
      - postgres_password
  
  celery-worker:
    secrets:
      - postgres_password
```
