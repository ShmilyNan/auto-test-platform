#!/usr/bin/env python
"""
执行流程诊断脚本
用于排查 Allure 目录不创建的问题
"""
import asyncio
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import async_session_maker
from plan.repository import ExecutionRecordRepository
from core.config import settings
from core.logger import logger


async def diagnose_execution(execution_id: int = None):
    """诊断执行记录"""
    async with async_session_maker() as session:
        repo = ExecutionRecordRepository(session)

        if execution_id:
            # 检查指定执行记录
            execution = await repo.get_by_id(execution_id)
            if not execution:
                print(f"❌ 执行记录 {execution_id} 不存在")
                return

            print(f"\n{'=' * 60}")
            print(f"执行记录详情 (ID: {execution_id})")
            print(f"{'=' * 60}")
            print(f"  状态: {execution.status}")
            print(f"  计划ID: {execution.plan_id}")
            print(f"  触发者: {execution.triggered_by}")
            print(f"  触发类型: {execution.trigger_type}")
            print(f"  开始时间: {execution.start_time}")
            print(f"  结束时间: {execution.end_time}")
            print(f"  持续时间: {execution.duration}s")
            print(f"  总用例数: {execution.total_cases}")
            print(f"  通过: {execution.passed_cases}")
            print(f"  失败: {execution.failed_cases}")
            print(f"  错误信息: {execution.error_message}")
            print(f"  Allure路径(UUID): {execution.allure_results_path}")
            print(f"  报告URL: {execution.report_url}")
            print(f"  创建时间: {execution.created_at}")

            # 检查目录是否存在
            allure_dir = os.path.join(settings.ALLURE_RESULTS_DIR, execution.allure_results_path or "")
            print(f"\n{'=' * 60}")
            print(f"目录检查")
            print(f"{'=' * 60}")
            print(f"  ALLURE_RESULTS_DIR: {settings.ALLURE_RESULTS_DIR}")
            print(f"  期望目录: {allure_dir}")
            print(f"  目录存在: {os.path.exists(allure_dir)}")

            if os.path.exists(settings.ALLURE_RESULTS_DIR):
                existing_dirs = os.listdir(settings.ALLURE_RESULTS_DIR)
                print(f"  现有子目录数: {len(existing_dirs)}")
                if existing_dirs:
                    print(f"  现有子目录示例: {existing_dirs[:5]}")
        else:
            # 列出最近的执行记录
            print(f"\n{'=' * 60}")
            print(f"最近5条执行记录")
            print(f"{'=' * 60}")

            from sqlalchemy import select, desc
            from plan.models import ExecutionRecord

            result = await session.execute(
                select(ExecutionRecord)
                .order_by(desc(ExecutionRecord.id))
                .limit(5)
            )
            executions = result.scalars().all()

            for ex in executions:
                allure_dir = os.path.join(settings.ALLURE_RESULTS_DIR, ex.allure_results_path or "")
                dir_exists = os.path.exists(allure_dir)
                status_icon = "✅" if ex.status == "finished" else "❌" if ex.status == "failed" else "⏳"
                dir_icon = "📁" if dir_exists else "❓"

                print(f"\n  {status_icon} ID={ex.id}, 状态={ex.status}, "
                      f"UUID={ex.allure_results_path[:8] if ex.allure_results_path else 'None'}..., "
                      f"{dir_icon} 目录={'存在' if dir_exists else '不存在'}")
                print(f"      错误: {ex.error_message or '无'}")


async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="执行流程诊断")
    parser.add_argument("--id", type=int, help="执行记录ID")
    args = parser.parse_args()

    await diagnose_execution(args.id)


if __name__ == "__main__":
    asyncio.run(main())
