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
from config.config import settings

logger = get_logger()


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
        
        # TODO: 实现从testcase模块获取用例并执行
        # 这里需要依赖注入testcase service
        
        return {
            "case_ids": case_ids,
            "status": "success"
        }
    
    async def run_yaml(self, yaml_file: str) -> Dict[str, Any]:
        """运行YAML测试文件"""
        logger.info(f"开始运行YAML测试: file={yaml_file}")
        
        # TODO: 实现YAML文件解析和执行
        
        return {
            "yaml_file": yaml_file,
            "status": "success"
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
