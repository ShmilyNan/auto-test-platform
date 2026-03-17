"""
常量定义模块
集中管理所有常量，避免硬编码
"""
from enum import Enum
from pathlib import Path


# ============================================
# HTTP状态码
# ============================================
class HTTPStatus:
    """HTTP状态码常量"""
    # 2xx 成功
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 4xx 客户端错误
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422

    # 5xx 服务器错误
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503


# ============================================
# 枚举类型
# ============================================

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class ProjectRole(str, Enum):
    """项目角色枚举"""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TriggerType(str, Enum):
    """触发类型枚举"""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    API = "api"


class HTTPMethod(str, Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AssertionType(str, Enum):
    """断言类型枚举"""
    STATUS_CODE = "status_code"
    RESPONSE_TIME = "response_time"
    JSON_PATH = "json_path"
    REGEX = "regex"
    HEADER = "header"
    BODY_CONTAINS = "body_contains"
    CONTENT_TYPE = "content_type"
    JSON_SCHEMA = "json_schema"


class CompareOperator(str, Enum):
    """比较运算符枚举"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    REGEX_MATCH = "regex_match"


class Environment(str, Enum):
    """环境标识枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageType(str, Enum):
    """存储类型枚举"""
    LOCAL = "local"
    OSS = "oss"
    S3 = "s3"


class ScheduleFrequency(str, Enum):
    """定时任务频率枚举"""
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduleType(str, Enum):
    """计划类型枚举"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    API_TRIGGERED = "api_triggered"


class NotificationType(str, Enum):
    """通知类型枚举"""
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    SLACK = "slack"


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TestCasePriority(str, Enum):
    """测试用例优先级枚举"""
    P0 = "p0"  # 冒烟测试
    P1 = "p1"  # 核心功能
    P2 = "p2"  # 一般功能
    P3 = "p3"  # 边缘场景

# ============================================
# 权限定义
# ============================================
PERMISSIONS = {
    ProjectRole.ADMIN.value: ["create", "read", "update", "delete", "execute", "manage"],
    ProjectRole.MEMBER.value: ["create", "read", "update", "execute"],
    ProjectRole.VIEWER.value: ["read"],
}


# ============================================
# 默认配置值
# ============================================

# 分页
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 超时时间（秒）
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 600

# 执行配置
MAX_CONCURRENT_EXECUTIONS = 10  # 最大并发执行数
EXECUTION_RETENTION_DAYS = 30   # 执行记录保留天数

# 重试配置
MAX_RETRY_COUNT = 3
RETRY_DELAY = 1  # 重试延迟（秒）


# ============================================
# 任务优先级
# ============================================

TASK_PRIORITY_HIGH = 1
TASK_PRIORITY_NORMAL = 5
TASK_PRIORITY_LOW = 10


# ============================================
# 错误码定义
# ============================================

class ErrorCode:
    """错误码定义"""
    # 通用错误
    SUCCESS = 0
    UNKNOWN = -1
    INVALID_PARAM = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    CONFLICT = 1005
    INTERNAL_ERROR = 1006

    # 数据库错误
    DATABASE_ERROR = 2001
    REDIS_ERROR = 2002
    CELERY_ERROR = 2003

    # 业务错误
    EXECUTION_ERROR = 3001
    REPORT_ERROR = 3002

# 项目路径
# ========================================
# 项目根路径
# ========================================
PROJECT_ROOT = Path(__file__).parent.parent
# ========================================
# 配置文件路径
# ========================================
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
# ========================================
# 测试输出文件路径
# ========================================
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = OUTPUT_DIR / "logs"
REPORT_DIR = OUTPUT_DIR / "reports"
ALLURE_RESULTS_DIR = REPORT_DIR / "allure"
ALLURE_REPORT_DIR = REPORT_DIR / "allure-report"
STORAGE_PATH = OUTPUT_DIR / "storage"