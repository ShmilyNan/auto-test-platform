"""
自动化测试平台 - 主入口
环境判断优先级（从高到低）：
1. 命令行参数 --env 或 -e
2. 环境变量 COZE_PROJECT_ENV（沙箱提供）
3. 环境变量 ENVIRONMENT
4. 默认值 dev
启动方式：
- 开发环境：python main.py 或 python main.py --env dev
- 生产环境：python main.py --env prod
- Docker 部署：自动检测 COZE_PROJECT_ENV 或 ENVIRONMENT 环境变量
"""
import argparse
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from core.config import settings, reset_settings, detect_environment, Environment
from core.database import init_db, close_db
from core.logger import setup_logging, logger
from api.v1 import api_router


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="自动化测试平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        示例:
          python main.py                    # 默认开发环境
          python main.py --env prod         # 生产环境
          python main.py -e dev             # 开发环境
          uvicorn main:app --host 0.0.0.0 --port 5000  # uvicorn 方式启动
                """
    )
    parser.add_argument(
        "--env", "-e",
        type=str,
        choices=["dev", "prod", "development", "production"],
        help="运行环境：dev（开发）或 prod（生产）"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址（默认：0.0.0.0）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="监听端口（默认：5000）"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（仅开发环境）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Worker 进程数（仅生产环境）"
    )

    return parser.parse_args()


def init_environment(env_arg: str = None):
    """
    初始化环境配置
    Args:
        env_arg: 命令行传入的环境参数
    """
    import os

    # 如果命令行指定了环境，设置到环境变量中
    if env_arg:
        env_value = "prod" if env_arg in ("prod", "production") else "dev"
        os.environ["ENVIRONMENT"] = env_value
        logger.info(f"从命令行参数设置环境: {env_value}")

    # 重置配置实例以重新加载环境
    reset_settings()

    # 输出环境信息
    env = detect_environment()
    logger.info(f"检测到运行环境: {env.value}")
    logger.info(f"配置摘要: {settings}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    setup_logging()
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"运行环境: {settings.ENVIRONMENT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"数据库: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    await init_db()

    # 初始化定时任务调度器
    if settings.SCHEDULE_ENABLED:
        from scheduler import start_scheduler
        start_scheduler()
        logger.info("定时任务调度器已启动")

    yield

    # 关闭时清理
    if settings.SCHEDULE_ENABLED:
        from scheduler import stop_scheduler
        stop_scheduler()
        logger.info("定时任务调度器已停止")

    await close_db()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    # docs_url=settings.DOCS_URL if settings.DEBUG else None,  # 生产环境禁用文档
    docs_url=settings.DOCS_URL,  # 生产环境禁用文档
    # redoc_url=settings.REDOC_URL if settings.DEBUG else None,
    redoc_url=settings.REDOC_URL,
    # openapi_url="/openapi.json" if settings.DEBUG else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix=settings.API_PREFIX)

# 挂载报告静态目录，提供 Allure HTML 报告访问
os.makedirs(settings.ALLURE_REPORT_DIR, exist_ok=True)
app.mount(
    "/reports",
    StaticFiles(directory=settings.ALLURE_REPORT_DIR, html=True),
    name="reports",
)

@app.get("/", tags=["Root"])
async def root():
    """根路径健康检查"""
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    args = parse_args()

    # 初始化环境
    init_environment(args.env)

    # 根据环境选择启动方式
    if settings.is_production:
        # 生产环境：使用 Gunicorn + Uvicorn Worker
        logger.info(f"生产环境启动: host={args.host}, port={args.port}, workers={args.workers}")
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_config=None,  # 禁用 uvicorn 默认日志配置，使用 loguru
        )
    else:
        # 开发环境：启用热重载
        logger.info(f"开发环境启动: host={args.host}, port={args.port}, reload={args.reload or True}")
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_config=None,  # 禁用 uvicorn 默认日志配置，使用 loguru
        )
