"""
配置管理模块
支持从 config.yaml、pyproject.toml 和 .env 文件加载配置
配置优先级: 环境变量 > .env > config.yaml > 默认值
"""
from typing import Any, Dict
from functools import lru_cache
from ruamel.yaml import YAML
import toml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import *

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


def load_yaml_config() -> Dict[str, Any]:
    """加载YAML配置文件"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return _yaml.load(f) or {}
    return {}


def load_toml_config() -> Dict[str, Any]:
    """加载TOML配置文件"""
    config_path = Path("pyproject.toml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return toml.load(f) or {}
    return {}


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # ============================================
    # 敏感配置（从环境变量读取）
    # ============================================

    # 数据库
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://autotest_user:776462@localhost:5432/autotest_platform",
        description="数据库连接URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery Broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery结果后端URL"
    )

    # JWT
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        description="JWT密钥"
    )

    # 环境
    ENVIRONMENT: str = Field(
        default=Environment.DEVELOPMENT.value,
        description="运行环境"
    )
    DEBUG: bool = Field(
        default=True,
        description="调试模式"
    )

    # ============================================
    # 应用配置（从YAML读取）
    # ============================================

    APP_NAME: str = "自动化测试平台"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "模块化单体架构的自动化测试平台"

    # API配置
    API_PREFIX: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # 数据库配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # Redis配置
    REDIS_DB_CACHE: int = 0
    REDIS_DB_CELERY_BROKER: int = 1
    REDIS_DB_CELERY_BACKEND: int = 2

    # Celery配置
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_TASK_TIME_LIMIT: int = 1800
    CELERY_TASK_SOFT_TIME_LIMIT: int = 1500
    CELERY_RESULT_EXPIRES: int = 86400

    # JWT配置
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 测试执行配置
    ALLURE_RESULTS_DIR: str = ALLURE_RESULTS_DIR
    ALLURE_REPORT_DIR: str = ALLURE_REPORT_DIR
    MAX_CONCURRENT_EXECUTIONS: int = 5
    DEFAULT_TIMEOUT: int = DEFAULT_TIMEOUT
    MAX_TIMEOUT: int = MAX_TIMEOUT

    # 存储配置
    STORAGE_TYPE: str = StorageType.LOCAL.value
    STORAGE_PATH: str = STORAGE_PATH

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    LOG_COMPRESSION: str = "zip"
    LOG_CONSOLE_OUTPUT: bool = True
    LOG_FILE_OUTPUT: bool = True
    LOG_DIR: str = "logs"

    # 定时任务配置
    SCHEDULE_ENABLED: bool = True
    SCHEDULE_TIMEZONE: str = "Asia/Shanghai"

    # 分页配置
    DEFAULT_PAGE_SIZE: int = DEFAULT_PAGE_SIZE
    MAX_PAGE_SIZE: int = MAX_PAGE_SIZE

    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_yaml_config()

    def _load_yaml_config(self):
        """从YAML文件加载配置"""
        yaml_config = load_yaml_config()

        # 应用配置
        app_config = yaml_config.get("app", {})
        self.APP_NAME = app_config.get("name", self.APP_NAME)
        self.APP_VERSION = app_config.get("version", self.APP_VERSION)
        self.APP_DESCRIPTION = app_config.get("description", self.APP_DESCRIPTION)
        self.DEBUG = app_config.get("debug", self.DEBUG)
        self.ENVIRONMENT = app_config.get("environment", self.ENVIRONMENT)

        # API配置
        api_config = yaml_config.get("api", {})
        self.API_PREFIX = api_config.get("prefix", self.API_PREFIX)
        self.DOCS_URL = api_config.get("docs_url", self.DOCS_URL)
        self.REDOC_URL = api_config.get("redoc_url", self.REDOC_URL)

        # 数据库配置
        db_config = yaml_config.get("database", {})
        self.DB_POOL_SIZE = db_config.get("pool_size", self.DB_POOL_SIZE)
        self.DB_MAX_OVERFLOW = db_config.get("max_overflow", self.DB_MAX_OVERFLOW)
        self.DB_POOL_PRE_PING = db_config.get("pool_pre_ping", self.DB_POOL_PRE_PING)
        self.DB_ECHO = db_config.get("echo", self.DB_ECHO)

        # Redis配置
        redis_config = yaml_config.get("redis", {})
        self.REDIS_DB_CACHE = redis_config.get("db_cache", self.REDIS_DB_CACHE)
        self.REDIS_DB_CELERY_BROKER = redis_config.get("db_celery_broker", self.REDIS_DB_CELERY_BROKER)
        self.REDIS_DB_CELERY_BACKEND = redis_config.get("db_celery_backend", self.REDIS_DB_CELERY_BACKEND)

        # Celery配置
        celery_config = yaml_config.get("celery", {})
        self.CELERY_WORKER_CONCURRENCY = celery_config.get("worker_concurrency", self.CELERY_WORKER_CONCURRENCY)
        self.CELERY_WORKER_PREFETCH_MULTIPLIER = celery_config.get("worker_prefetch_multiplier", self.CELERY_WORKER_PREFETCH_MULTIPLIER)
        self.CELERY_TASK_TIME_LIMIT = celery_config.get("task_time_limit", self.CELERY_TASK_TIME_LIMIT)
        self.CELERY_TASK_SOFT_TIME_LIMIT = celery_config.get("task_soft_time_limit", self.CELERY_TASK_SOFT_TIME_LIMIT)
        self.CELERY_RESULT_EXPIRES = celery_config.get("result_expires", self.CELERY_RESULT_EXPIRES)

        # JWT配置
        jwt_config = yaml_config.get("jwt", {})
        self.JWT_ALGORITHM = jwt_config.get("algorithm", self.JWT_ALGORITHM)
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = jwt_config.get("access_token_expire_minutes", self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = jwt_config.get("refresh_token_expire_days", self.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        # 测试执行配置
        test_config = yaml_config.get("test_execution", {})
        self.TEST_RESULTS_DIR = test_config.get("results_dir", self.TEST_RESULTS_DIR)
        self.ALLURE_RESULTS_DIR = test_config.get("allure_results_dir", self.ALLURE_RESULTS_DIR)
        self.MAX_CONCURRENT_EXECUTIONS = test_config.get("max_concurrent_executions", self.MAX_CONCURRENT_EXECUTIONS)
        self.DEFAULT_TIMEOUT = test_config.get("default_timeout", self.DEFAULT_TIMEOUT)
        self.MAX_TIMEOUT = test_config.get("max_timeout", self.MAX_TIMEOUT)

        # 存储配置
        storage_config = yaml_config.get("storage", {})
        self.STORAGE_TYPE = storage_config.get("type", self.STORAGE_TYPE)
        self.STORAGE_PATH = storage_config.get("path", self.STORAGE_PATH)

        # 日志配置
        log_config = yaml_config.get("logging", {})
        self.LOG_LEVEL = log_config.get("level", self.LOG_LEVEL)
        self.LOG_FORMAT = log_config.get("format", self.LOG_FORMAT)
        self.LOG_ROTATION = log_config.get("rotation", self.LOG_ROTATION)
        self.LOG_RETENTION = log_config.get("retention", self.LOG_RETENTION)
        self.LOG_COMPRESSION = log_config.get("compression", self.LOG_COMPRESSION)
        self.LOG_CONSOLE_OUTPUT = log_config.get("console_output", self.LOG_CONSOLE_OUTPUT)
        self.LOG_FILE_OUTPUT = log_config.get("file_output", self.LOG_FILE_OUTPUT)
        self.LOG_DIR = log_config.get("log_dir", self.LOG_DIR)

        # 定时任务配置
        schedule_config = yaml_config.get("schedule", {})
        self.SCHEDULE_ENABLED = schedule_config.get("enabled", self.SCHEDULE_ENABLED)
        self.SCHEDULE_TIMEZONE = schedule_config.get("timezone", self.SCHEDULE_TIMEZONE)

        # 分页配置
        pagination_config = yaml_config.get("pagination", {})
        self.DEFAULT_PAGE_SIZE = pagination_config.get("default_page_size", self.DEFAULT_PAGE_SIZE)
        self.MAX_PAGE_SIZE = pagination_config.get("max_page_size", self.MAX_PAGE_SIZE)

        # 限流配置
        rate_limit_config = yaml_config.get("rate_limit", {})
        self.RATE_LIMIT_ENABLED = rate_limit_config.get("enabled", self.RATE_LIMIT_ENABLED)
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = rate_limit_config.get("requests_per_minute", self.RATE_LIMIT_REQUESTS_PER_MINUTE)
        self.RATE_LIMIT_BURST = rate_limit_config.get("burst", self.RATE_LIMIT_BURST)

    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT.value

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.ENVIRONMENT == Environment.PRODUCTION.value

    @property
    def is_staging(self) -> bool:
        """是否预发布环境"""
        return self.ENVIRONMENT == Environment.STAGING.value


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
