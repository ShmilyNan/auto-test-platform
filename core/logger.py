"""
日志模块 - 使用loguru统一管理日志
接管所有第三方库的日志输出，保证格式一致
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from loguru import logger
from core.config import settings

# 移除默认的handler
logger.remove()

# 日志格式
LOG_FORMAT = settings.LOG_FORMAT

# 日志级别映射
LOG_LEVELS = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class InterceptHandler(logging.Handler):
    """
    拦截标准logging日志，转发到loguru
    用于接管第三方库的日志输出
    """

    def emit(self, record: logging.LogRecord) -> None:
        # 获取对应的loguru日志级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者信息
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """
    配置日志系统
    - 配置loguru的输出格式和目标
    - 拦截所有第三方库的日志
    """
    # 创建日志目录
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取日志级别
    log_level = settings.LOG_LEVEL.upper()

    # 添加控制台输出
    if settings.LOG_CONSOLE_OUTPUT:
        logger.add(
            sys.stdout,
            format=LOG_FORMAT,
            level=log_level,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=settings.DEBUG,
        )

    # 添加文件输出
    if settings.LOG_FILE_OUTPUT:
        # 主日志文件
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format=LOG_FORMAT,
            level=log_level,
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression=settings.LOG_COMPRESSION,
            enqueue=True,
            backtrace=True,
            diagnose=settings.DEBUG,
            encoding="utf-8",
        )

        # 错误日志单独输出
        logger.add(
            log_dir / "error_{time:YYYY-MM-DD}.log",
            format=LOG_FORMAT,
            level="ERROR",
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression=settings.LOG_COMPRESSION,
            enqueue=True,
            backtrace=True,
            diagnose=True,  # 错误日志始终显示详细信息
            encoding="utf-8",
        )

    # 拦截所有标准logging日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 设置常见第三方库的日志级别
    # FastAPI/Uvicorn
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]

    # SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

    # Celery
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("celery.worker").setLevel(logging.INFO)

    # Redis
    logging.getLogger("redis").setLevel(logging.WARNING)

    # HTTPX
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Alembic
    logging.getLogger("alembic").setLevel(logging.INFO)

    # Pydantic
    logging.getLogger("pydantic").setLevel(logging.WARNING)

    logger.info(f"日志系统初始化完成 - 环境: {settings.ENVIRONMENT}, 级别: {log_level}")


def get_logger(name: Optional[str] = None):
    """
    获取logger实例
    Args:
        name: 模块名称，用于标识日志来源
    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 提供便捷方法
def log_debug(message: str, **kwargs):
    """调试日志"""
    logger.debug(message, **kwargs)


def log_info(message: str, **kwargs):
    """信息日志"""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """警告日志"""
    logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    """错误日志"""
    logger.error(message, **kwargs)


def log_critical(message: str, **kwargs):
    """严重错误日志"""
    logger.critical(message, **kwargs)


def log_exception(message: str, **kwargs):
    """异常日志（包含堆栈）"""
    logger.exception(message, **kwargs)


def log_success(message: str, **kwargs):
    """成功日志"""
    logger.success(message, **kwargs)
