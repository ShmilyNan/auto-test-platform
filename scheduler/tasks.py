"""
定时任务实现
包含系统的各种定时任务
"""
import os
import shutil
from datetime import datetime, timedelta, timezone
from celery import shared_task
from config.config import settings
from core.logger import logger
from core.database import async_session_maker


@shared_task(name="scheduler.tasks.check_and_execute_scheduled_plans")
def check_and_execute_scheduled_plans():
    """
    检查并执行到期的测试计划
    每分钟执行一次
    """
    import asyncio

    async def _check():
        from plan.repository import TestPlanRepository
        from plan.service import PlanService

        async with async_session_maker() as session:
            plan_repo = TestPlanRepository(session)
            plan_service = PlanService(session)

            # 获取所有启用的定时计划
            # TODO: 实现根据cron表达式判断是否应该执行
            logger.debug("检查定时测试计划...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_check())
    finally:
        loop.close()


@shared_task(name="scheduler.tasks.cleanup_old_executions")
def cleanup_old_executions(days: int = 30):
    """
    清理旧的执行记录
    每小时执行一次
    """
    import asyncio

    async def _cleanup():
        from plan.repository import ExecutionRecordRepository

        async with async_session_maker() as session:
            execution_repo = ExecutionRecordRepository(session)

            # 计算 cutoff 日期
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            logger.info(f"开始清理 {cutoff_date} 之前的执行记录")

            # TODO: 实现删除逻辑
            # 这里可以保留统计信息，删除详细数据

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_cleanup())
        logger.info("执行记录清理完成")
    except Exception as e:
        logger.error(f"执行记录清理失败: {e}")
    finally:
        loop.close()


@shared_task(name="scheduler.tasks.cleanup_temp_files")
def cleanup_temp_files():
    """
    清理临时文件
    每天凌晨2点执行
    """
    try:
        # 清理测试结果目录
        results_dir = settings.TEST_RESULTS_DIR
        if os.path.exists(results_dir):
            for item in os.listdir(results_dir):
                item_path = os.path.join(results_dir, item)
                if os.path.isdir(item_path):
                    # 获取目录修改时间
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if datetime.now() - mtime > timedelta(days=7):
                        shutil.rmtree(item_path)
                        logger.info(f"清理临时目录: {item_path}")

        # 清理Allure结果目录
        allure_dir = settings.ALLURE_RESULTS_DIR
        if os.path.exists(allure_dir):
            for item in os.listdir(allure_dir):
                item_path = os.path.join(allure_dir, item)
                if os.path.isdir(item_path):
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if datetime.now() - mtime > timedelta(days=7):
                        shutil.rmtree(item_path)
                        logger.info(f"清理Allure目录: {item_path}")

        logger.info("临时文件清理完成")
    except Exception as e:
        logger.error(f"临时文件清理失败: {e}")


@shared_task(name="scheduler.tasks.generate_daily_statistics")
def generate_daily_statistics():
    """
    生成每日统计报告
    每天凌晨1点执行
    """
    import asyncio

    async def _generate():
        from stats.service import StatsService
        from project.repository import ProjectRepository

        async with async_session_maker() as session:
            project_repo = ProjectRepository(session)
            stats_service = StatsService()

            # 获取所有项目
            projects = await project_repo.list()

            for project in projects:
                try:
                    # 获取项目统计
                    stats = await stats_service.get_project_stats(project.id)

                    # TODO: 保存每日统计记录
                    logger.info(f"项目 {project.name} 每日统计: {stats}")
                except Exception as e:
                    logger.error(f"项目 {project.name} 统计生成失败: {e}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_generate())
        logger.info("每日统计报告生成完成")
    except Exception as e:
        logger.error(f"每日统计报告生成失败: {e}")
    finally:
        loop.close()


@shared_task(name="scheduler.tasks.check_timeout_executions")
def check_timeout_executions():
    """
    检查执行超时的任务
    每5分钟执行一次
    """
    import asyncio

    async def _check():
        from plan.models import ExecutionRecord
        from sqlalchemy import select, and_

        async with async_session_maker() as session:
            # 查找运行中且超时的执行记录
            timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.MAX_TIMEOUT)

            result = await session.execute(
                select(ExecutionRecord).where(
                    and_(
                        ExecutionRecord.status == "running",
                        ExecutionRecord.start_time < timeout_threshold
                    )
                )
            )

            timeout_executions = result.scalars().all()

            for execution in timeout_executions:
                execution.status = "failed"
                execution.error_message = "执行超时"
                execution.end_time = datetime.now(timezone.utc)
                logger.warning(f"执行记录 {execution.id} 已超时，已标记为失败")

            await session.commit()

            if timeout_executions:
                logger.info(f"已处理 {len(timeout_executions)} 个超时执行记录")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_check())
    except Exception as e:
        logger.error(f"检查超时任务失败: {e}")
    finally:
        loop.close()


@shared_task(name="scheduler.tasks.send_execution_notification")
def send_execution_notification(execution_id: int, status: str):
    """
    发送执行完成通知
    """
    # TODO: 实现通知发送逻辑（邮件、钉钉、企业微信等）
    logger.info(f"执行记录 {execution_id} 完成，状态: {status}")
    pass


@shared_task(name="scheduler.tasks.sync_test_results")
def sync_test_results(execution_id: int):
    """
    同步测试结果到存储
    """
    import asyncio

    async def _sync():
        from report.service import ReportService

        report_service = ReportService()
        await report_service.generate_report(execution_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_sync())
        logger.info(f"执行记录 {execution_id} 结果同步完成")
    except Exception as e:
        logger.error(f"执行记录 {execution_id} 结果同步失败: {e}")
    finally:
        loop.close()
