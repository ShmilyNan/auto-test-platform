# Docker Swarm 部署指南

## 目录
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [部署步骤](#部署步骤)
- [服务管理](#服务管理)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)
- [备份与恢复](#备份与恢复)

## 环境要求

### 硬件要求
- **Master节点**: 4核CPU, 8GB内存, 100GB磁盘
- **Worker节点**: 4核CPU, 8GB内存, 50GB磁盘

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Linux操作系统（推荐Ubuntu 20.04/22.04）

### 网络要求
- 节点间网络互通
- 开放端口：
  - 2377/tcp - Swarm集群管理
  - 7946/tcp+udp - 节点间通信
  - 4789/udp - Overlay网络
  - 80/tcp - HTTP
  - 443/tcp - HTTPS

## 快速开始

### 1. 准备环境变量

```bash
# 复制环境变量模板
cp .env.production .env

# 编辑配置
vim .env
```

**必须修改的配置**：
```bash
POSTGRES_PASSWORD=your_secure_password_here
SECRET_KEY=your-super-secret-key-at-least-32-characters-long
```

### 2. 初始化Swarm

```bash
# 在主节点执行
docker swarm init --advertise-addr <MANAGER-IP>

# 其他节点加入集群（在worker节点执行）
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

### 3. 部署服务

```bash
# 给脚本执行权限
chmod +x deploy.sh

# 部署
./deploy.sh init
./deploy.sh deploy
```

### 4. 验证部署

```bash
# 查看服务状态
./deploy.sh status

# 查看健康状态
./deploy.sh health
```

## 配置说明

### docker-stack.yml 配置详解

#### 服务配置

**API服务**：
```yaml
deploy:
  mode: replicated
  replicas: 2          # 副本数，可根据负载调整
  update_config:
    parallelism: 1     # 同时更新1个副本
    delay: 10s         # 更新间隔
    failure_action: rollback  # 失败时回滚
  resources:
    limits:
      cpus: '2'        # 最大CPU
      memory: 2G       # 最大内存
```

**Celery Worker**：
```yaml
deploy:
  replicas: 2          # Worker数量
  resources:
    limits:
      cpus: '4'        # Worker需要更多CPU
      memory: 4G
```

#### 网络配置

```yaml
networks:
  autotest-network:
    driver: overlay    # Overlay网络
    attachable: true   # 允许独立容器连接
    driver_opts:
      encrypted: true  # 加密通信
```

#### 存储卷配置

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/autotest/postgres  # 宿主机路径
```

### 资源规划

| 服务 | 副本数 | CPU限制 | 内存限制 | 说明 |
|------|--------|---------|----------|------|
| postgres | 1 | 2核 | 2GB | 数据库 |
| redis | 1 | 1核 | 1GB | 缓存 |
| api | 2-4 | 2核 | 2GB | API服务 |
| celery-worker | 2-4 | 4核 | 4GB | 测试执行器 |
| celery-beat | 1 | 0.5核 | 512MB | 定时调度器 |
| nginx | 1 | 1核 | 512MB | 反向代理 |

## 部署步骤

### 方式一：使用部署脚本（推荐）

```bash
# 1. 初始化
./deploy.sh init

# 2. 部署
./deploy.sh deploy

# 3. 查看状态
./deploy.sh status
```

### 方式二：手动部署

```bash
# 1. 创建数据目录
sudo mkdir -p /data/autotest/{postgres,redis,storage,logs}

# 2. 创建网络
docker network create --driver overlay --attachable autotest-network

# 3. 加载环境变量
export $(cat .env | grep -v '^#' | xargs)

# 4. 部署服务栈
docker stack deploy -c docker-stack.yml autotest

# 5. 查看服务
docker stack services autotest
```

### 方式三：使用CI/CD

创建 `.gitlab-ci.yml` 或 GitHub Actions：

```yaml
# GitLab CI示例
deploy:
  stage: deploy
  script:
    - docker build -t $REGISTRY/autotest-platform:$CI_COMMIT_SHA .
    - docker push $REGISTRY/autotest-platform:$CI_COMMIT_SHA
    - docker stack deploy -c docker-stack.yml --with-registry-auth autotest
  only:
    - main
```

## 服务管理

### 服务操作

```bash
# 更新服务
./deploy.sh update api

# 回滚服务
./deploy.sh rollback api

# 扩缩容
./deploy.sh scale api 3

# 查看日志
./deploy.sh logs api

# 健康检查
./deploy.sh health
```

### 手动操作

```bash
# 查看所有服务
docker stack services autotest

# 查看服务详情
docker service inspect autotest_api

# 查看服务日志
docker service logs -f autotest_api

# 更新服务镜像
docker service update --image registry.example.com/autotest-platform:v1.0.0 autotest_api

# 强制重启服务
docker service update --force autotest_api

# 扩缩容
docker service scale autotest_api=3

# 回滚
docker service rollback autotest_api
```

## 监控与日志

### 服务监控

```bash
# 实时监控服务状态
watch -n 1 'docker stack services autotest'

# 查看服务任务
docker stack ps autotest

# 查看资源使用
docker stats $(docker ps -q)
```

### 日志查看

```bash
# API服务日志
docker service logs -f autotest_api --tail 100

# Celery Worker日志
docker service logs -f autotest_celery-worker --tail 100

# 所有服务日志
for svc in api celery-worker celery-beat; do
  echo "=== $svc logs ==="
  docker service logs autotest_$svc --tail 50
done
```

### 应用日志

```bash
# 进入容器查看
docker exec -it $(docker ps -q -f name=autotest_api) bash
tail -f /app/logs/app.log

# 或者直接查看宿主机日志
tail -f /data/autotest/logs/app.log
```

## 故障排查

### 常见问题

#### 1. 服务启动失败

```bash
# 查看服务状态
docker service ps autotest_api --no-trunc

# 查看错误信息
docker service logs autotest_api
```

**可能原因**：
- 镜像不存在
- 环境变量配置错误
- 网络连接问题

#### 2. 数据库连接失败

```bash
# 检查数据库服务
docker service ps autotest_postgres

# 测试数据库连接
docker exec -it $(docker ps -q -f name=autotest_postgres) \
  psql -U autotest_user -d autotest_platform -c "SELECT 1"
```

#### 3. Redis连接失败

```bash
# 检查Redis服务
docker service ps autotest_redis

# 测试Redis连接
docker exec -it $(docker ps -q -f name=autotest_redis) redis-cli ping
```

#### 4. 服务无响应

```bash
# 检查健康状态
curl http://localhost/health

# 检查资源使用
docker stats $(docker ps -q -f name=autotest_api)

# 重启服务
docker service update --force autotest_api
```

### 排查流程

```bash
# 1. 检查服务状态
docker stack services autotest

# 2. 查看任务状态
docker stack ps autotest

# 3. 查看日志
docker service logs autotest_api --tail 100

# 4. 进入容器排查
docker exec -it <container-id> bash

# 5. 检查网络
docker network inspect autotest-network

# 6. 检查存储
ls -la /data/autotest/
```

## 备份与恢复

### 数据备份

```bash
# 创建备份脚本
cat > backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec $(docker ps -q -f name=autotest_postgres) \
  pg_dump -U autotest_user autotest_platform > $BACKUP_DIR/database.sql

# 备份Redis
docker exec $(docker ps -q -f name=autotest_redis) \
  redis-cli BGSAVE
docker cp $(docker ps -q -f name=autotest_redis):/data/dump.rdb $BACKUP_DIR/

# 备份存储
tar -czf $BACKUP_DIR/storage.tar.gz /data/autotest/storage

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh
```

### 数据恢复

```bash
# 恢复数据库
cat /backup/20240115_100000/database.sql | \
  docker exec -i $(docker ps -q -f name=autotest_postgres) \
  psql -U autotest_user autotest_platform

# 恢复Redis
docker cp /backup/20240115_100000/dump.rdb \
  $(docker ps -q -f name=autotest_redis):/data/
docker service update --force autotest_redis

# 恢复存储
tar -xzf /backup/20240115_100000/storage.tar.gz -C /
```

### 定时备份

```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

## 安全配置

### 1. 修改默认密码

```bash
# 生成强密码
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

# 更新.env文件
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${POSTGRES_PASSWORD}/" .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
```

### 2. 配置防火墙

```bash
# 只允许特定IP访问
ufw allow from 10.0.0.0/8 to any port 2377
ufw allow from 10.0.0.0/8 to any port 7946
ufw allow from 10.0.0.0/8 to any port 4789
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 3. 启用TLS

```bash
# 使用Let's Encrypt
certbot certonly --standalone -d yourdomain.com

# 复制证书
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## 性能优化

### 1. 资源调整

根据实际负载调整副本数和资源限制：

```yaml
# 高负载配置
api:
  deploy:
    replicas: 4
    resources:
      limits:
        cpus: '4'
        memory: 4G

celery-worker:
  deploy:
    replicas: 6
    resources:
      limits:
        cpus: '8'
        memory: 8G
```

### 2. 数据库优化

```sql
-- 调整连接池
ALTER SYSTEM SET max_connections = 200;

-- 创建索引
CREATE INDEX idx_execution_records_status ON execution_records(status);
CREATE INDEX idx_execution_records_created_at ON execution_records(created_at);
```

### 3. Redis优化

```bash
# 调整内存限制
docker service update \
  --args "redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru" \
  autotest_redis
```

## 升级指南

### 滚动升级

```bash
# 1. 构建新镜像
docker build -t registry.example.com/autotest-platform:v1.1.0 .
docker push registry.example.com/autotest-platform:v1.1.0

# 2. 更新服务（滚动更新）
docker service update \
  --image registry.example.com/autotest-platform:v1.1.0 \
  --update-parallelism 1 \
  --update-delay 30s \
  autotest_api

# 3. 验证升级
docker service ps autotest_api
```

### 数据库迁移

```bash
# 执行数据库迁移
docker exec $(docker ps -q -f name=autotest_api) \
  alembic upgrade head
```

## 附录

### Docker Swarm常用命令

```bash
# 查看节点
docker node ls

# 查看服务
docker service ls

# 查看任务
docker service ps <service>

# 查看网络
docker network ls

# 查看存储卷
docker volume ls

# 查看服务日志
docker service logs <service>

# 更新服务
docker service update <service> <options>

# 扩缩容
docker service scale <service>=<replicas>

# 回滚
docker service rollback <service>
```

### 参考资料

- [Docker Swarm官方文档](https://docs.docker.com/engine/swarm/)
- [Docker Stack部署](https://docs.docker.com/engine/reference/commandline/stack_deploy/)
- [Celery生产环境部署](https://docs.celeryq.dev/en/stable/userguide/deployment.html)
