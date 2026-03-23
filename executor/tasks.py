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
    """
    在当前进程中直接执行测试任务。
    Args:
        execution_id: 执行记录ID
    Returns:
        执行结果字典
    """
    from executor.service import ExecutorService

    logger.info(f"[本地执行] 开始执行测试任务: execution_id={execution_id}")

    try:
        executor = ExecutorService()
        result = await executor.execute(execution_id)
        logger.info(f"[本地执行] 测试任务执行完成: execution_id={execution_id}, result={result}")
        return result
    except Exception as e:
        logger.error(f"[本地执行] 测试任务执行失败: execution_id={execution_id}, error={str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def dispatch_test_execution(execution_id: int, background_tasks=None) -> str:
    """
    分发测试执行任务。
    执行优先级：
    1. Celery 分布式任务队列
    2. FastAPI BackgroundTasks（如果 Celery 不可用）
    3. 同步执行（最后的备选方案）
    Args:
        execution_id: 执行记录ID
        background_tasks: FastAPI BackgroundTasks 实例
    Returns:
        分发类型: "celery", "background_tasks", "sync"
    """
    logger.info(f"[任务分发] 开始分发测试任务: execution_id={execution_id}")

    # 1. 尝试使用 Celery
    try:
        task_result = execute_test_task.delay(execution_id)
        task_id = getattr(task_result, "id", None)
        logger.info(f"[任务分发] ✅ Celery 分发成功: execution_id={execution_id}, task_id={task_id}")
        return "celery"
    except Exception as exc:
        logger.warning(f"[任务分发] ⚠️ Celery 分发失败，准备回退: execution_id={execution_id}, error={exc}")

    # 2. 回退到 BackgroundTasks
    if background_tasks is not None:
        try:
            background_tasks.add_task(_run_async_task_sync, execution_id)
            logger.info(f"[任务分发] ✅ BackgroundTasks 分发成功: execution_id={execution_id}")
            return "background_tasks"

        except Exception as exc:
            logger.error(f"[任务分发] ❌ BackgroundTasks 分发失败: {exc}")

    # 3. 同步执行（最后的备选方案）
    logger.warning(f"[任务分发] ⚠️ 所有异步方式失败，使用同步执行: execution_id={execution_id}")
    try:
        asyncio.run(execute_test_task_local(execution_id))
        logger.info(f"[任务分发] ✅ 同步执行完成: execution_id={execution_id}")
        return "sync"
    except Exception as exc:
        logger.error(f"[任务分发] ❌ 同步执行失败: execution_id={execution_id}, error={exc}")
        raise


def _run_async_task_sync(execution_id: int):
    """
    同步包装器，用于在 BackgroundTasks 中运行异步任务。
    这个函数会在新的线程中创建新的事件循环来执行异步任务。
    Args:
        execution_id: 执行记录ID
    """
    import concurrent.futures

    logger.info(f"[后台任务] 开始执行: execution_id={execution_id}")

    try:
        # 使用线程池执行，确保有独立的事件循环
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, execute_test_task_local(execution_id))
            result = future.result(timeout=1800)  # 30分钟超时
            logger.info(f"[后台任务] 执行完成: execution_id={execution_id}, result={result}")
            return result
    except Exception as e:
        logger.error(f"[后台任务] 执行失败: execution_id={execution_id}, error={str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task()
def execute_test_task(execution_id: int):
    """执行测试任务（Celery worker 调用）"""
    import asyncio
    from executor.service import ExecutorService

    logger.info(f"[Celery] 开始执行测试任务: execution_id={execution_id}")
    
    # 创建事件循环并执行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        executor = ExecutorService()
        result = loop.run_until_complete(executor.execute(execution_id))
        logger.info(f"[Celery] 测试任务执行完成: execution_id={execution_id}, result={result}")
        return result
    except Exception as e:
        logger.error(f"[Celery] 测试任务执行失败: execution_id={execution_id}, error={str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        loop.close()


@celery_app.task()
def generate_report_task(execution_id: int):
    """生成报告任务"""
    import asyncio
    from report.service import ReportService
    
    logger.info(f"[Celery] 开始生成报告: execution_id={execution_id}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        report_service = ReportService()
        result = loop.run_until_complete(report_service.generate_report(execution_id))
        logger.info(f"[Celery] 报告生成完成: execution_id={execution_id}")
        return result
    except Exception as e:
        logger.error(f"[Celery] 报告生成失败: execution_id={execution_id}, error={str(e)}")
        raise
    finally:
        loop.close()


# 导入所有模型（顺序很重要：先导入被依赖的表）
# 1. 用户表（被多个表引用）
from user.models import User  # noqa: F401

# 2. 项目表（被测试计划、执行记录等引用）
from project.models import Project, ProjectMember  # noqa: F401

# 3. 测试用例相关表
from testcase.models import TestCase, TestSuite  # noqa: F401

# 4. 测试计划相关表
from plan.models import TestPlan, ExecutionRecord, ExecutionResult  # noqa: F401

# 5. 统计表
from stats.models import DailyStats


if __name__ == "__main__":
    celery_app.start()
