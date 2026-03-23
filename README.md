# 自动化测试平台后端

基于 FastAPI 的模块化单体架构自动化测试平台后端。

## 项目架构

### 技术栈
- **框架**: FastAPI + Uvicorn + Gunicorn
- **数据库**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0（异步）
- **迁移**: Alembic
- **缓存/队列**: Redis 7
- **任务队列**: Celery + Celery Beat
- **认证**: JWT (python-jose)
- **测试框架**: pytest + Allure
- **日志**: Loguru

### 模块划分

```
├── core/              # 核心模块：配置、数据库、日志、安全
├── user/              # 用户模块：认证、权限管理
├── project/           # 项目模块：项目管理、成员关联
├── testcase/          # 测试用例模块：用例管理
├── plan/              # 测试计划模块：计划管理、执行调度
├── executor/          # 执行引擎：pytest集成、异步执行
├── report/            # 报告模块：Allure报告生成
├── stats/             # 统计模块：数据统计
├── scheduler/         # 定时任务：Celery Beat调度
└── api/v1/            # API路由层
    └── endpoints/     # 各模块端点
```

## 快速开始

### 环境要求
- Python 3.14+
- Docker & Docker Compose
- Make（可选）

### 使用Docker Compose启动（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd autotest-platform

# 2. 配置环境变量
cp .env.dev.example .env.dev
# 编辑.env文件，修改敏感配置

# 3. 启动所有服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f api

# 5. 运行数据库迁移
docker-compose exec api alembic upgrade head
```

### 开发环境启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动开发数据库
make dev
# 或
docker-compose -f docker-compose.dev.yml up -d

# 3. 配置环境变量
cp .env.dev.example .env.dev

# 4. 运行数据库迁移
alembic upgrade head

# 5. 启动API服务
make run
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 6. 启动Celery Worker（新终端）
make worker
# 或
celery -A scheduler worker --loglevel=info --concurrency=4

# 7. 启动Celery Beat（新终端）
make beat
# 或
celery -A scheduler beat --loglevel=info
```

### 使用Make命令

```bash
make help           # 显示所有可用命令
make install        # 安装依赖
make dev            # 启动开发环境数据库
make run            # 启动开发服务器
make worker         # 启动Celery Worker
make beat           # 启动Celery Beat
make build          # 构建Docker镜像
make up             # 启动生产环境
make down           # 停止生产环境
make test           # 运行测试
make migrate        # 运行数据库迁移
make clean          # 清理临时文件
```

## 配置说明

### 配置文件结构

项目采用分层配置管理：

```
├── config.yaml          # 应用配置（非敏感）
├── pyproject.toml       # 项目元数据和工具配置
├── .env                 # 环境变量（敏感信息）
└── .env.example         # 环境变量模板
```

### 配置优先级

环境变量 > .env > config.yaml > 默认值

### 主要配置项

#### 数据库配置（.env）
```env
DATABASE_URL=postgresql+asyncpg://autotest_user:776462@localhost:5432/autotest_platform
```

#### Redis配置（.env）
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

#### JWT配置（.env）
```env
SECRET_KEY=your-super-secret-key-change-in-production
```

#### 应用配置（config.yaml）
```yaml
app:
  name: "自动化测试平台"
  version: "1.0.0"
  debug: false
  environment: "production"
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc

## 主要API端点

### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录

### 项目
- `POST /api/v1/projects/` - 创建项目
- `GET /api/v1/projects/` - 获取项目列表
- `POST /api/v1/projects/{id}/members` - 添加成员

### 测试用例
- `POST /api/v1/testcases/cases` - 创建测试用例
- `GET /api/v1/testcases/cases` - 获取用例列表
- `POST /api/v1/testcases/suites` - 创建用例集

### 测试计划
- `POST /api/v1/plans/` - 创建测试计划
- `POST /api/v1/plans/{id}/run` - 执行测试计划
- `GET /api/v1/plans/{id}/executions` - 执行记录

### 报告和统计
- `GET /api/v1/reports/{execution_id}` - 获取报告
- `GET /api/v1/stats/project/{project_id}` - 项目统计

## 定时任务

系统内置以下定时任务：

| 任务 | 频率 | 说明 |
|------|------|------|
| check-scheduled-plans | 每分钟 | 检查待执行的测试计划 |
| cleanup-old-executions | 每小时 | 清理过期执行记录 |
| cleanup-temp-files | 每天2:00 | 清理临时文件 |
| generate-daily-stats | 每天1:00 | 生成每日统计 |
| check-timeout-executions | 每5分钟 | 检查超时任务 |

## 生产部署

### Docker Compose部署

```bash
# 构建并启动
docker-compose up -d --build

# 扩展API实例
docker-compose up -d --scale api=3

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 水平扩展

```bash
# 扩展API服务
docker-compose up -d --scale api=4 --no-recreate

# 扩展Worker
docker-compose up -d --scale celery-worker=4 --no-recreate
```

### Nginx配置（生产环境）

```bash
# 启动包含Nginx的生产环境
docker-compose --profile production up -d
```

## 日志系统

使用Loguru统一管理日志：

```python
from core.logger import logger

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
logger.exception("异常日志")  # 自动包含堆栈信息
```

日志文件位置：
- 应用日志：`logs/app_YYYY-MM-DD.log`
- 错误日志：`logs/error_YYYY-MM-DD.log`

## 开发指南

### 代码规范

```bash
# 格式化代码
make format

# 代码检查
make lint
```

### 数据库迁移

```bash
# 创建迁移
make migration
# 输入迁移描述后自动生成

# 执行迁移
make migrate

# 重置数据库
make db-reset
```

### 运行测试

```bash
make test
```

## 监控和健康检查

- 健康检查端点：`GET /health`
- Docker健康检查：内置在Dockerfile中
- Celery监控：`flower`（可选安装）

## 故障排查

### 数据库连接问题
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 查看数据库日志
docker-compose logs postgres
```

### Redis连接问题
```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 查看Redis日志
docker-compose logs redis
```

### Celery问题
```bash
# 查看Worker日志
docker-compose logs celery-worker

# 查看Beat日志
docker-compose logs celery-beat
```

## 许可证

MIT License
