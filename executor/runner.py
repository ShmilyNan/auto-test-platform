"""
独立执行器 - 支持作为纯后端接口自动化框架运行
"""
import asyncio
import argparse
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from executor.service import ExecutorService
from core.logger import get_logger, setup_logging
from core.config import settings

logger = get_logger(__name__)


class TestRunner:
    """测试执行器"""

    def __init__(self):
        self.executor = ExecutorService()

    async def run_plan(self, plan_id: int) -> Dict[str, Any]:
        """运行测试计划"""
        logger.info(f"开始运行测试计划: plan_id={plan_id}")

        # 准备测试用例
        test_cases = await self.executor.prepare_test_cases(plan_id)

        # 执行测试
        # 这里简化处理，实际应该创建执行记录
        import tempfile
        test_dir = tempfile.mkdtemp(prefix="test_run_")
        allure_dir = os.path.join(settings.ALLURE_RESULTS_DIR, f"plan_{plan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(allure_dir, exist_ok=True)

        # 生成pytest文件
        await self.executor.generate_pytest_files(test_cases, test_dir)

        # 运行pytest
        pytest_result = await self.executor.run_pytest(test_dir, allure_dir)

        # 解析结果
        allure_result = await self.executor.parse_allure_results(allure_dir)

        logger.info(f"测试计划执行完成: plan_id={plan_id}, result={allure_result}")

        return {
            "plan_id": plan_id,
            "allure_dir": allure_dir,
            "result": allure_result
        }

    async def run_cases(self, case_ids: List[int]) -> Dict[str, Any]:
        """运行指定用例"""
        logger.info(f"开始运行测试用例: case_ids={case_ids}")

        from core.database import async_session_maker
        from testcase.repository import TestCaseRepository
        from executor.service import ExecutorService

        async with async_session_maker() as session:
            case_repo = TestCaseRepository(session)
            executor = ExecutorService()

            results = []
            for case_id in case_ids:
                case = await case_repo.get_by_id(case_id)
                if not case:
                    logger.warning(f"用例 {case_id} 不存在")
                    continue

                # 执行单个用例
                result = await executor.execute_single_case(case)
                results.append(result)

            return {
                "case_ids": case_ids,
                "results": results,
                "total": len(results),
                "passed": sum(1 for r in results if r.get("status") == "passed"),
                "failed": sum(1 for r in results if r.get("status") == "failed"),
                "status": "success"
            }

    async def run_yaml(self, yaml_file: str) -> Dict[str, Any]:
        """运行YAML测试文件"""
        logger.info(f"开始运行YAML测试: file={yaml_file}")

        from executor.parser import YAMLParser
        from executor.service import ExecutorService

        try:
            # 解析YAML文件
            parser = YAMLParser()
            test_cases = parser.parse_file(yaml_file)

            # 执行解析出的测试用例
            executor = ExecutorService()
            results = []

            for case_data in test_cases:
                result = await executor.execute_single_case(case_data)
                results.append(result)

            return {
                "yaml_file": yaml_file,
                "results": results,
                "total": len(results),
                "passed": sum(1 for r in results if r.get("status") == "passed"),
                "failed": sum(1 for r in results if r.get("status") == "failed"),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"YAML测试执行失败: {e}")
            return {
                "yaml_file": yaml_file,
                "error": str(e),
                "status": "failed"
            }


async def main():
    """主函数"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="自动化测试执行器")
    parser.add_argument("--plan", type=int, help="测试计划ID")
    parser.add_argument("--cases", type=str, help="测试用例ID列表，逗号分隔")
    parser.add_argument("--yaml", type=str, help="YAML测试文件路径")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.plan:
        result = await runner.run_plan(args.plan)
        print(json.dumps(result, indent=2))
    elif args.cases:
        case_ids = [int(id) for id in args.cases.split(",")]
        result = await runner.run_cases(case_ids)
        print(json.dumps(result, indent=2))
    elif args.yaml:
        result = await runner.run_yaml(args.yaml)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
