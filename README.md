# 自动化测试平台后端

基于 FastAPI 的模块化单体架构自动化测试平台后端。

## 项目架构

### 技术栈
- **框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL（支持 SQLite 开发环境）
- **ORM**: SQLAlchemy 2.0（异步）
- **迁移**: Alembic
- **认证**: JWT (python-jose)
- **任务队列**: Celery + Redis
- **测试框架**: pytest + Allure

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
└── api/v1/            # API路由层
    └── endpoints/     # 各模块端点
```

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 12+（或使用 SQLite）
- Redis 6+（可选，用于Celery）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_platform

# Redis配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT配置
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 测试执行配置
TEST_RESULTS_DIR=/tmp/test_results
ALLURE_RESULTS_DIR=/tmp/allure_results
```

### 数据库迁移

```bash
# 初始化数据库（首次运行）
alembic upgrade head
```

### 启动服务

```bash
# 开发环境
uvicorn main:app --host 0.0.0.0 --port 5000 --reload

# 生产环境
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
```

### 启动Celery Worker（可选）

```bash
celery -A executor.tasks worker --loglevel=info
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc

## 主要API端点

### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录

### 用户
- `GET /api/v1/users/` - 获取用户列表
- `GET /api/v1/users/{user_id}` - 获取用户详情
- `PUT /api/v1/users/{user_id}` - 更新用户信息

### 项目
- `POST /api/v1/projects/` - 创建项目
- `GET /api/v1/projects/` - 获取项目列表
- `GET /api/v1/projects/{project_id}` - 获取项目详情
- `POST /api/v1/projects/{project_id}/members` - 添加项目成员

### 测试用例
- `POST /api/v1/testcases/cases` - 创建测试用例
- `GET /api/v1/testcases/cases` - 获取用例列表
- `POST /api/v1/testcases/suites` - 创建用例集

### 测试计划
- `POST /api/v1/plans/` - 创建测试计划
- `POST /api/v1/plans/{plan_id}/run` - 执行测试计划
- `GET /api/v1/plans/{plan_id}/executions` - 获取执行记录

### 报告
- `GET /api/v1/reports/{execution_id}` - 获取报告

### 统计
- `GET /api/v1/stats/project/{project_id}` - 获取项目统计
- `GET /api/v1/stats/project/{project_id}/execution-trend` - 执行趋势

## 核心特性

### 1. 模块化设计
- 每个模块独立封装，通过接口抽象实现解耦
- 支持未来向微服务架构平滑演进

### 2. 异步执行
- 使用Celery实现测试任务异步执行
- 支持定时任务调度

### 3. 测试执行引擎
- 基于pytest的测试执行框架
- 自动生成Allure报告
- 支持用例断言和变量提取

### 4. 完整的权限管理
- 基于JWT的身份认证
- 项目级别的权限控制

## 开发指南

### 代码规范
- 遵循 PEP 8 规范
- 使用类型注解
- 编写单元测试

### 数据库迁移
```bash
# 创建迁移脚本
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

### 独立运行执行器
```bash
# 运行测试计划
python -m executor.runner --plan 1

# 运行指定用例
python -m executor.runner --cases 1,2,3
```

## 部署建议

### Docker部署
```bash
# 构建镜像
docker build -t test-platform .

# 运行容器
docker run -p 5000:5000 test-platform
```

### 生产环境配置
1. 使用 PostgreSQL 作为数据库
2. 使用 Redis 作为缓存和消息队列
3. 配置 HTTPS
4. 使用 Supervisor 或 K8s 管理进程

## 许可证

MIT License
