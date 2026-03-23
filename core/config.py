"""
配置管理模块
支持多环境配置：dev（开发环境）和 prod（生产环境）

配置加载优先级（从高到低）:
1. Docker Secrets（生产环境敏感信息）
2. 环境变量
3. 环境特定的 .env 文件（.env.dev 或 .env.prod）
4. 环境特定的 YAML 文件（config/config.dev.yaml 或 config/config.prod.yaml）
5. 基础 YAML 文件（config/config.base.yaml）
6. 代码中的默认值

环境判断优先级（从高到低）:
1. 命令行参数 --env 或 -e
2. 环境变量 COZE_PROJECT_ENV（沙箱提供）
3. 环境变量 ENVIRONMENT
4. 默认值 dev
"""
import sys
import argparse
from typing import Any, Dict, Optional
from functools import lru_cache
from pathlib import Path
from ruamel.yaml import YAML
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import Environment, PROJECT_ROOT
from loguru import logger

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


# ============================================
# 环境检测
# ============================================

def detect_environment() -> Environment:
    """
    检测当前运行环境
    优先级（从高到低）:
    1. 命令行参数 --env 或 -e
    2. 环境变量 COZE_PROJECT_ENV（沙箱提供）
    3. 环境变量 ENVIRONMENT
    4. 默认值 dev
    注意：此函数在 Settings 初始化之前调用，不会加载 .env 文件
    Returns:
        Environment 枚举值
    """
    import os

    # 1. 检查命令行参数
    env_from_args = _parse_env_from_args()
    if env_from_args:
        return Environment.from_string(env_from_args)

    # 2. 检查环境变量 COZE_PROJECT_ENV（沙箱提供）
    coze_env = os.getenv("COZE_PROJECT_ENV", "").strip()
    if coze_env:
        return Environment.from_string(coze_env)

    # 3. 检查环境变量 ENVIRONMENT（注意：此时 .env 文件尚未加载）
    env_var = os.getenv("ENVIRONMENT", "").strip()
    if env_var:
        return Environment.from_string(env_var)

    # 4. 默认开发环境
    return Environment.DEV


def _parse_env_from_args() -> Optional[str]:
    """从命令行参数解析环境配置"""
    # 查找 --env 或 -e 参数
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--env", "-e"):
            if i + 1 < len(args):
                return args[i + 1]
        elif arg.startswith("--env="):
            return arg.split("=", 1)[1]
        elif arg.startswith("-e="):
            return arg.split("=", 1)[1]
    return None


# ============================================
# 配置文件加载
# ============================================

def read_secret(secret_name: str) -> Optional[str]:
    """
    从 Docker Secrets 文件读取敏感信息

    Docker Swarm 将 secrets 挂载到 /run/secrets/<secret_name>

    Args:
        secret_name: secret 名称

    Returns:
        secret 内容，如果不存在返回 None
    """
    import os

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


def load_yaml_config(environment: Environment) -> Dict[str, Any]:
    """
    加载 YAML 配置文件

    加载顺序（后加载的覆盖前面的）:
    1. config/config.base.yaml（基础配置）
    2. config/config.{env}.yaml（环境特定配置）

    Args:
        environment: 当前环境

    Returns:
        合并后的配置字典
    """
    config: Dict[str, Any] = {}

    # 配置目录
    config_dir = PROJECT_ROOT / "config"

    # 1. 加载基础配置
    base_config_path = config_dir / "config.base.yaml"
    if base_config_path.exists():
        with open(base_config_path, "r", encoding="utf-8") as f:
            base_config = _yaml.load(f) or {}
            config = _deep_merge(config, base_config)
            logger.debug(f"加载基础配置: {base_config_path}")

    # 2. 加载环境特定配置
    env_config_name = f"config.{environment.value}.yaml"
    env_config_path = config_dir / env_config_name
    if env_config_path.exists():
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_config = _yaml.load(f) or {}
            config = _deep_merge(config, env_config)
            logger.debug(f"加载环境配置: {env_config_path}")
    else:
        logger.debug(f"环境配置文件不存在: {env_config_path}")

    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",  # 加载默认 .env 文件
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # ============================================
    # 环境标识
    # ============================================

    _environment: Environment = Environment.DEV
    ENVIRONMENT: str = Field(
        default="dev",
        description="运行环境：dev（开发）或 prod（生产）"
    )
    DEBUG: bool = Field(
        default=True,
        description="调试模式"
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
    ALLURE_RESULTS_DIR: str = ""
    ALLURE_REPORT_DIR: str = ""
    MAX_CONCURRENT_EXECUTIONS: int = 5
    DEFAULT_TIMEOUT: int = 30
    MAX_TIMEOUT: int = 600

    # 存储配置
    STORAGE_TYPE: str = "local"
    STORAGE_PATH: str = ""

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
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # 项目域名（用于生成报告URL等）
    COZE_PROJECT_DOMAIN_DEFAULT: str = Field(
        default="",
        description="项目对外访问域名"
    )

    def __init__(self, **kwargs):
        # 1. 先调用父类初始化（读取环境变量和 .env 文件）
        super().__init__(**kwargs)

        # 2. 检测环境（优先级：命令行 > COZE_PROJECT_ENV > ENVIRONMENT 环境变量 > 默认值）
        # 注意：必须在 super().__init__() 之后调用，因为我们需要读取环境变量
        self._environment = detect_environment()

        # 3. 强制设置环境标识（确保检测到的环境值不被 .env 文件覆盖）
        self.ENVIRONMENT = self._environment.value
        self.DEBUG = self._environment == Environment.DEV

        # 4. 从 Docker Secrets 加载敏感信息
        self._load_secrets()

        # 5. 从 YAML 文件加载配置
        self._load_yaml_config()

        # 6. 构建连接 URL
        self._build_connection_urls()

        # 7. 设置路径配置
        self._setup_paths()

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
        yaml_config = load_yaml_config(self._environment)

        # 应用配置
        app_config = yaml_config.get("app", {})
        self.APP_NAME = app_config.get("name", self.APP_NAME)
        self.APP_VERSION = app_config.get("version", self.APP_VERSION)
        self.APP_DESCRIPTION = app_config.get("description", self.APP_DESCRIPTION)

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
        self.MAX_CONCURRENT_EXECUTIONS = test_config.get("max_concurrent_executions", self.MAX_CONCURRENT_EXECUTIONS)
        self.DEFAULT_TIMEOUT = test_config.get("default_timeout", self.DEFAULT_TIMEOUT)
        self.MAX_TIMEOUT = test_config.get("max_timeout", self.MAX_TIMEOUT)

        # 存储配置
        storage_config = yaml_config.get("storage", {})
        self.STORAGE_TYPE = storage_config.get("type", self.STORAGE_TYPE)

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

    def _setup_paths(self):
        """设置路径配置（根据环境区分）"""
        from .constants import (
            OUTPUT_DIR, LOG_DIR, REPORT_DIR,
            ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR, STORAGE_PATH
        )

        # 开发环境：使用项目目录下的相对路径
        # 生产环境：使用 /app 下的路径（Docker 容器内）
        if self._environment == Environment.PROD:
            # 生产环境路径（Docker 容器内）
            self.LOG_DIR = "/app/logs"
            self.ALLURE_RESULTS_DIR = "/app/output/reports/allure"
            self.ALLURE_REPORT_DIR = "/app/output/reports/allure-report"
            self.STORAGE_PATH = "/app/output/storage"
        else:
            # 开发环境路径（使用 constants.py 中定义的路径）
            self.LOG_DIR = str(LOG_DIR)
            self.ALLURE_RESULTS_DIR = str(ALLURE_RESULTS_DIR)
            self.ALLURE_REPORT_DIR = str(ALLURE_REPORT_DIR)
            self.STORAGE_PATH = str(STORAGE_PATH)

    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self._environment == Environment.DEV

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self._environment == Environment.PROD

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

        return "environment"

    def __repr__(self) -> str:
        return (
            f"Settings(environment={self.ENVIRONMENT}, "
            f"debug={self.DEBUG}, "
            f"db={self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}, "
            f"redis={self.REDIS_HOST}:{self.REDIS_PORT})"
        )


# ============================================
# 全局配置实例
# ============================================

_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings():
    """重置配置实例（用于测试或切换环境）"""
    global _settings_instance
    _settings_instance = None


# 全局配置实例
settings = get_settings()
