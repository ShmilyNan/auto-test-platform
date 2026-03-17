"""
Celery任务定义
"""
from celery import Celery
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# 创建Celery应用
celery_app = Celery(
    "test_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["executor.tasks"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100
)


@celery_app.task(bind=True)
def execute_test_task(execution_id: int):
    """执行测试任务"""
    import asyncio
    from executor.service import ExecutorService
    
    logger.info(f"开始执行测试任务: execution_id={execution_id}")
    
    # 创建事件循环并执行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        executor = ExecutorService()
        result = loop.run_until_complete(executor.execute(execution_id))
        logger.info(f"测试任务执行完成: execution_id={execution_id}, result={result}")
        return result
    except Exception as e:
        logger.error(f"测试任务执行失败: execution_id={execution_id}, error={str(e)}")
        raise
    finally:
        loop.close()


@celery_app.task(bind=True)
def generate_report_task(execution_id: int):
    """生成报告任务"""
    import asyncio
    from report.service import ReportService
    
    logger.info(f"开始生成报告: execution_id={execution_id}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        report_service = ReportService()
        result = loop.run_until_complete(report_service.generate_report(execution_id))
        logger.info(f"报告生成完成: execution_id={execution_id}")
        return result
    except Exception as e:
        logger.error(f"报告生成失败: execution_id={execution_id}, error={str(e)}")
        raise
    finally:
        loop.close()


if __name__ == "__main__":
    celery_app.start()
