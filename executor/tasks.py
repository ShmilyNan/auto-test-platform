"""
Celery任务定义
"""
import asyncio
from celery import Celery
from core.config import settings
from core.logger import logger


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


async def execute_test_task_local(execution_id: int):
    """在当前进程中直接执行测试任务。"""
    from executor.service import ExecutorService

    logger.info(f"使用本地回退方式执行测试任务: execution_id={execution_id}")
    executor = ExecutorService()
    return await executor.execute(execution_id)


def dispatch_test_execution(execution_id: int, background_tasks=None) -> str:
    """分发测试执行任务；当Celery不可用时回退到当前进程后台执行。"""
    try:
        task_result = execute_test_task.delay(execution_id)
        task_id = getattr(task_result, "id", None)
        logger.info(f"测试任务已提交到Celery: execution_id={execution_id}, task_id={task_id}")
        return "celery"
    except Exception as exc:
        logger.warning(
            f"Celery分发测试任务失败，回退到本地后台执行: execution_id={execution_id}, error={exc}"
        )

        if background_tasks is not None:
            background_tasks.add_task(execute_test_task_local, execution_id)
            return "background_tasks"

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(execute_test_task_local(execution_id))
            return "asyncio"
        except RuntimeError:
            asyncio.run(execute_test_task_local(execution_id))
            return "inline"


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
