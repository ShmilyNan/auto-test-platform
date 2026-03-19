"""
配置管理模块
支持从 config.yaml和 Docker Secrets 加载配置
配置优先级: Docker Secrets > 环境变量 > .env > config.yaml > 默认值
注意: pyproject.toml 仅用于开发工具配置（black, isort, mypy, pytest等）
      项目元数据和业务配置统一在 config.yaml 中管理
"""
from typing import Any, Dict, Optional
from functools import lru_cache
from ruamel.yaml import YAML
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import *
from loguru import logger

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


def read_secret(secret_name: str) -> Optional[str]:
    """
    从 Docker Secrets 文件读取敏感信息
    Docker Swarm 将 secrets 挂载到 /run/secrets/<secret_name>
    Args:
        secret_name: secret 名称
    Returns:
        secret 内容，如果不存在返回 None
    """
    # Docker secrets 默认路径
    secret_path = Path(f"/run/secrets/{secret_name}")

    if secret_path.exists():
        try:
            content = secret_path.read_text().strip()
            logger.debug(f"成功从 Docker Secret 读取: {secret_name}")
            return content
        except Exception as e:
            logger.warning(f"读取 Docker Secret 失败 [{secret_name}]: {e}")

    return None


def load_yaml_config() -> Dict[str, Any]:
    """加载YAML配置文件"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return _yaml.load(f) or {}
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
    # 敏感配置（优先从 Docker Secrets 读取）
    # ============================================

    # 数据库密码
    _postgres_password: Optional[str] = None
    POSTGRES_PASSWORD: str = Field(
        default="",
        description="PostgreSQL 密码（从 Secret 或环境变量读取）"
    )

    # 数据库连接信息
    DATABASE_HOST: str = Field(
        default="localhost",
        description="数据库主机"
    )
    DATABASE_PORT: int = Field(
        default=5432,
        description="数据库端口"
    )
    DATABASE_USER: str = Field(
        default="autotest_user",
        description="数据库用户"
    )
    DATABASE_NAME: str = Field(
        default="autotest_platform",
        description="数据库名称"
    )

    # 完整数据库URL（由其他字段构建）
    DATABASE_URL: str = Field(
        default="",
        description="数据库连接URL"
    )

    # Redis连接信息
    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis主机"
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="Redis端口"
    )
    REDIS_DB_CACHE: int = Field(
        default=0,
        description="Redis缓存数据库"
    )
    REDIS_DB_CELERY_BROKER: int = Field(
        default=1,
        description="Celery Broker 数据库"
    )
    REDIS_DB_CELERY_BACKEND: int = Field(
        default=2,
        description="Celery Backend 数据库"
    )

    # Redis URL（由其他字段构建）
    REDIS_URL: str = Field(
        default="",
        description="Redis连接URL"
    )
    CELERY_BROKER_URL: str = Field(
        default="",
        description="Celery Broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="",
        description="Celery结果后端URL"
    )

    # JWT密钥
    _secret_key: Optional[str] = None
    SECRET_KEY: str = Field(
        default="",
        description="JWT密钥（从 Secret 或环境变量读取）"
    )

    # ============================================
    # 通知服务密钥（可选）
    # ============================================

    _smtp_password: Optional[str] = None
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP密码"
    )

    _dingtalk_webhook: Optional[str] = None
    DINGTALK_WEBHOOK: str = Field(
        default="",
        description="钉钉机器人Webhook"
    )

    _wechat_webhook: Optional[str] = None
    WECHAT_WEBHOOK: str = Field(
        default="",
        description="企业微信机器人Webhook"
    )

    # ============================================
    # 对象存储密钥（可选）
    # ============================================

    _oss_access_key: Optional[str] = None
    OSS_ACCESS_KEY: str = Field(
        default="",
        description="OSS访问密钥"
    )

    _oss_secret_key: Optional[str] = None
    OSS_SECRET_KEY: str = Field(
        default="",
        description="OSS密钥"
    )

    # ============================================
    # 应用配置（从YAML读取）
    # ============================================

    ENVIRONMENT: str = Field(
        default=Environment.DEVELOPMENT.value,
        description="运行环境"
    )
    DEBUG: bool = Field(
        default=True,
        description="调试模式"
    )
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
        self._load_secrets()
        self._load_yaml_config()
        self._build_connection_urls()

    def _load_secrets(self):
        """
        从 Docker Secrets 加载敏感信息
        优先级: Docker Secrets > 环境变量 > 默认值
        """
        # PostgreSQL 密码
        self._postgres_password = read_secret("postgres_password")
        if self._postgres_password:
            self.POSTGRES_PASSWORD = self._postgres_password

        # JWT 密钥
        self._secret_key = read_secret("secret_key")
        if self._secret_key:
            self.SECRET_KEY = self._secret_key

        # SMTP 密码
        self._smtp_password = read_secret("smtp_password")
        if self._smtp_password:
            self.SMTP_PASSWORD = self._smtp_password

        # 钉钉 Webhook
        self._dingtalk_webhook = read_secret("dingtalk_webhook")
        if self._dingtalk_webhook:
            self.DINGTALK_WEBHOOK = self._dingtalk_webhook

        # 微信 Webhook
        self._wechat_webhook = read_secret("wechat_webhook")
        if self._wechat_webhook:
            self.WECHAT_WEBHOOK = self._wechat_webhook

        # OSS 密钥
        self._oss_access_key = read_secret("oss_access_key")
        if self._oss_access_key:
            self.OSS_ACCESS_KEY = self._oss_access_key

        self._oss_secret_key = read_secret("oss_secret_key")
        if self._oss_secret_key:
            self.OSS_SECRET_KEY = self._oss_secret_key

    def _build_connection_urls(self):
        """构建数据库和 Redis 连接 URL"""
        # 构建数据库 URL
        if not self.DATABASE_URL:
            password = self.POSTGRES_PASSWORD or "776462"
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DATABASE_USER}:{password}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )

        # 构建 Redis URL
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CACHE}"

        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_BROKER}"

        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_BACKEND}"

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
        # self.ALLURE_RESULTS_DIR = test_config.get("allure_results_dir", self.ALLURE_RESULTS_DIR)
        # self.ALLURE_REPORT_DIR = test_config.get("allure_report_dir", self.ALLURE_REPORT_DIR)
        self.MAX_CONCURRENT_EXECUTIONS = test_config.get("max_concurrent_executions", self.MAX_CONCURRENT_EXECUTIONS)
        self.DEFAULT_TIMEOUT = test_config.get("default_timeout", self.DEFAULT_TIMEOUT)
        self.MAX_TIMEOUT = test_config.get("max_timeout", self.MAX_TIMEOUT)

        # 存储配置
        storage_config = yaml_config.get("storage", {})
        self.STORAGE_TYPE = storage_config.get("type", self.STORAGE_TYPE)
        # self.STORAGE_PATH = storage_config.get("path", self.STORAGE_PATH)

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

    def get_secret_source(self, secret_name: str) -> str:
        """
        获取 secret 的来源

        Args:
            secret_name: secret 名称

        Returns:
            来源描述: "docker_secret", "environment", "default"
        """
        secret_path = Path(f"/run/secrets/{secret_name}")
        if secret_path.exists():
            return "docker_secret"

        # 检查环境变量
        env_var = secret_name.upper()
        if env_var in self.model_dump():
            return "environment"

        return "default"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
