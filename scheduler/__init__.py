"""
定时任务调度器
使用Celery Beat实现定时任务调度
"""
from typing import Dict
from celery import Celery
from celery.schedules import crontab
from config.config import settings
from core.logger import logger

# 创建Celery应用
celery_app = Celery(
    "autotest_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery配置
celery_app.conf.update(
    # 序列化配置
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 时区配置
    timezone=settings.SCHEDULE_TIMEZONE,
    enable_utc=True,

    # Worker配置
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=100,

    # 任务配置
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    result_expires=settings.CELERY_RESULT_EXPIRES,

    # 包含任务模块
    imports=[
        "executor.tasks",
        "scheduler.tasks",
    ],
)

# ============================================
# 定时任务定义
# ============================================

CELERYBEAT_SCHEDULE = {
    # 每分钟检查待执行的测试计划
    "check-scheduled-plans": {
        "task": "scheduler.tasks.check_and_execute_scheduled_plans",
        "schedule": 60.0,  # 每60秒
        "options": {"queue": "schedule"},
    },
    # 每小时清理过期的执行记录
    "cleanup-old-executions": {
        "task": "scheduler.tasks.cleanup_old_executions",
        "schedule": crontab(minute=0),  # 每小时整点
        "options": {"queue": "maintenance"},
    },
    # 每天凌晨清理临时文件
    "cleanup-temp-files": {
        "task": "scheduler.tasks.cleanup_temp_files",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
        "options": {"queue": "maintenance"},
    },
    # 每天凌晨生成每日统计报告
    "generate-daily-stats": {
        "task": "scheduler.tasks.generate_daily_statistics",
        "schedule": crontab(hour=1, minute=0),  # 每天凌晨1点
        "options": {"queue": "stats"},
    },
    # 每5分钟检查执行超时的任务
    "check-timeout-executions": {
        "task": "scheduler.tasks.check_timeout_executions",
        "schedule": 300.0,  # 每5分钟
        "options": {"queue": "maintenance"},
    },
}

# 应用定时任务配置
celery_app.conf.beat_schedule = CELERYBEAT_SCHEDULE

# ============================================
# 调度器管理
# ============================================

_scheduler_instance = None


def start_scheduler():
    """启动调度器"""
    global _scheduler_instance

    if not settings.SCHEDULE_ENABLED:
        logger.info("定时任务调度已禁用")
        return

    # Celery Beat会在worker启动时自动运行
    logger.info("定时任务调度器配置已加载")
    logger.info(f"已注册 {len(CELERYBEAT_SCHEDULE)} 个定时任务")


def stop_scheduler():
    """停止调度器"""
    logger.info("定时任务调度器已停止")


def get_scheduler_status() -> Dict:
    """获取调度器状态"""
    return {
        "enabled": settings.SCHEDULE_ENABLED,
        "timezone": settings.SCHEDULE_TIMEZONE,
        "tasks": list(CELERYBEAT_SCHEDULE.keys()),
    }
