# WSL 环境下 Docker Swarm 部署故障排查指南

## 环境说明

- **操作系统**: Windows WSL2 (Ubuntu)
- **Docker**: Docker Desktop + WSL 2 集成
- **部署模式**: Docker Swarm 单节点

## 常见问题及解决方案

### 1. 服务一直处于 Pending 状态

**症状**:
```
ID                  NAME                MODE                REPLICAS            IMAGE
xyz123              autotest_api        replicated          0/1                 autotest-platform:latest
```

**原因分析**:

| 原因 | 检查方法                 | 解决方案 |
|------|----------------------|----------|
| 镜像不存在 | `docker images`      | `docker build -t autotest-platform:latest .` |
| placement constraints 不满足 | 检查 docker-stack.yaml | 移除 `node.role == manager` 约束 |
| 资源不足 | `docker info`        | 降低资源限制 |
| 网络问题 | `docker network ls`  | 创建 overlay 网络 |

**解决方案**:

```bash
# 检查服务任务详情
docker service ps autotest_api --no-trunc

# 查看错误信息
docker service inspect autotest_api --format '{{json .Status}}'

# 如果是约束问题，移除 constraints
# 使用 docker-stack.wsl.yaml
docker stack deploy -c docker-stack.wsl.yaml autotest
```

---

### 2. 服务启动后立即失败

**症状**:
```
autotest_api.1.xyz123    autotest-platform:latest   Running     5 seconds ago   Failed 2 seconds ago
```

**原因分析**:

| 原因 | 错误信息 | 解决方案 |
|------|----------|----------|
| 容器内路径不存在 | `mkdir: cannot create directory` | 修改 Dockerfile 创建目录 |
| 挂载失败 | `invalid mount config` | 使用 docker volume |
| 健康检查失败 | `health: starting` -> `unhealthy` | 延长 start_period |
| 依赖服务未就绪 | `connection refused` | 添加 depends_on + healthcheck |

**解决方案**:

```bash
# 查看失败任务详情
docker service ps autotest_api --no-trunc --filter desired-state=failed

# 查看容器日志
docker service logs autotest_api --tail 100

# 进入容器调试
docker run --rm -it autotest-platform:latest /bin/bash
```

---

### 3. Bind Mount 路径问题（WSL 最常见）

**症状**:
```
Error: error while creating mount source path '/data/autotest': mkdir /data/autotest: permission denied
```

**原因**:
- WSL 中 `/data` 目录可能不存在
- Docker Desktop 的文件系统隔离
- 权限问题

**解决方案 A: 创建目录**

```bash
sudo mkdir -p /data/autotest/{postgres,redis,storage,logs,allure-results,allure-report}
sudo chown -R $(whoami):$(whoami) /data/autotest
```

**解决方案 B: 使用 Docker Volume（推荐）**

修改 `docker-stack.yml`，使用 docker volume 代替 bind mount：

```yaml
# 原配置（bind mount）
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/autotest/postgres  # WSL 中可能不存在

# 新配置（docker volume）
volumes:
  postgres_data:
    driver: local  # Docker 自动管理
```

**推荐**: 使用 `docker-stack.wsl.yml`，已优化为 docker volume。

---

### 4. Secrets 问题

**症状**:
```
Error: rpc error: code = InvalidArgument desc = secret 'autotest_postgres_password' not found
```

**检查 Secrets 是否存在**:
```bash
docker secret ls
```

**解决方案**:
```bash
# 创建 Secrets
openssl rand -base64 32 | docker secret create autotest_postgres_password -

# 或使用脚本
./scripts/deploy-wsl.sh
```

---

### 5. 网络问题

**症状**:
```
Error: error creating external connectivity network: network autotest-network not found
```

**解决方案**:
```bash
# 创建 overlay 网络
docker network create --driver overlay --attachable autotest-network

# 检查网络
docker network ls
docker network inspect autotest-network
```

---

### 6. 内存/资源不足

**症状**:
- 服务启动后立即退出
- OOMKilled

**检查 WSL 内存限制**:
```bash
# 查看内存
free -h

# 查看 Docker 资源
docker info | grep -i memory
```

**解决方案**:

创建或编辑 `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

重启 WSL:
```powershell
wsl --shutdown
```

---

### 7. 健康检查失败

**症状**:
```
health: starting -> unhealthy
```

**原因**:
- start_period 太短
- 依赖服务未就绪

**解决方案**:

修改 `docker-stack.wsl.yml`:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "..."]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 120s  # 延长启动等待时间
```

---

### 8. Windows 防火墙阻止端口

**症状**:
- 容器正常运行
- 无法通过浏览器访问

**解决方案**:

```powershell
# 以管理员身份运行 PowerShell
# 允许端口
netsh advfirewall firewall add rule name="Docker API" dir=in action=allow protocol=tcp localport=5000

# 或者在 Docker Desktop 设置中勾选 "Expose daemon on tcp://localhost:2375 without TLS"
```

---

## 完整排查流程

### 步骤 1: 运行诊断脚本

```bash
chmod +x scripts/diagnose_swarm.sh
./scripts/diagnose_swarm.sh
```

### 步骤 2: 检查服务状态

```bash
# 查看所有服务
docker stack services autotest

# 查看任务状态
docker stack ps autotest

# 查看失败任务
docker stack ps autotest --filter desired-state=failed --no-trunc
```

### 步骤 3: 查看服务日志

```bash
# API 服务日志
docker service logs autotest_api --tail 100 -f

# 数据库日志
docker service logs autotest_postgres --tail 50

# Redis 日志
docker service logs autotest_redis --tail 50
```

### 步骤 4: 逐个启动服务调试

```bash
# 1. 先启动数据库
docker service create --name test-postgres \
  --secret source=autotest_postgres_password,target=postgres_password \
  -e POSTGRES_USER=autotest_user \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password \
  -e POSTGRES_DB=autotest_platform \
  postgres:15-alpine

# 检查是否正常
docker service ps test-postgres
docker service logs test-postgres

# 2. 再启动 Redis
docker service create --name test-redis redis:7-alpine

# 3. 最后启动 API
docker service create --name test-api \
  --secret source=autotest_postgres_password,target=postgres_password \
  --secret source=autotest_secret_key,target=secret_key \
  -e DATABASE_HOST=test-postgres \
  -e REDIS_HOST=test-redis \
  -p 5000:5000 \
  autotest-platform:latest
```

---

## 推荐部署方式

### 方式 1: 使用一键部署脚本（推荐）

```bash
chmod +x scripts/deploy-wsl.sh
./scripts/deploy-wsl.sh
```

### 方式 2: 手动部署

```bash
# 1. 初始化 Swarm
docker swarm init --advertise-addr 127.0.0.1

# 2. 创建网络
docker network create --driver overlay --attachable autotest-network

# 3. 创建 Secrets
openssl rand -base64 32 | docker secret create autotest_postgres_password -
openssl rand -base64 32 | docker secret create autotest_secret_key -

# 4. 构建镜像
docker build -t autotest-platform:latest .

# 5. 部署（使用 WSL 优化配置）
docker stack deploy -c docker-stack.wsl.yaml autotest

# 6. 检查状态
docker stack services autotest
docker stack ps autotest
```

---

## WSL 特殊配置

### 1. Docker Desktop 设置

确保以下设置已启用：
- ✅ Use WSL 2 based engine
- ✅ Settings > Resources > WSL Integration > 启用当前发行版

### 2. WSL 配置文件

创建 `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true

[experimental]
autoMemoryReclaim=gradual
```

### 3. Docker Desktop 资源设置

Settings > Resources:
- Memory: 至少 6GB
- CPU: 至少 2 核
- Disk image location: 确保有足够空间

---

## 常用命令速查

```bash
# 服务管理
docker stack ls                          # 列出所有 stack
docker stack services autotest           # 查看服务
docker stack ps autotest                 # 查看任务
docker stack rm autotest                 # 删除 stack

# 服务调试
docker service logs autotest_api -f      # 查看日志
docker service ps autotest_api --no-trunc # 详细任务状态
docker service inspect autotest_api      # 服务配置

# Secrets 管理
docker secret ls                         # 列出 secrets
docker secret inspect autotest_postgres_password

# 网络管理
docker network ls
docker network inspect autotest-network

# Swarm 管理
docker node ls                           # 列出节点
docker info | grep Swarm                 # Swarm 状态
docker swarm leave --force               # 退出 Swarm（谨慎使用）
```

---

## 问题排查检查清单

- [ ] Docker Desktop 正在运行
- [ ] WSL 2 集成已启用
- [ ] Swarm 已初始化 (`docker info | grep Swarm`)
- [ ] 镜像已构建 (`docker images | grep autotest-platform`)
- [ ] Secrets 已创建 (`docker secret ls`)
- [ ] 网络已创建 (`docker network ls | grep autotest-network`)
- [ ] 端口未被占用 (`netstat -an | grep 5000`)
- [ ] 资源充足 (`free -h`, `df -h`)
- [ ] 防火墙允许端口

---

## 联系支持

如果以上方法都无法解决问题，请收集以下信息：

```bash
# 收集诊断信息
./scripts/diagnose_swarm.sh > diagnosis.txt 2>&1

# 收集服务日志
docker service logs autotest_api > api.log 2>&1
docker service logs autotest_postgres > postgres.log 2>&1

# 系统 信息
docker version > docker-version.txt
docker info > docker-info.txt
```
