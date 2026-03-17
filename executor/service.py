"""
测试执行引擎服务层
"""
from typing import Dict, Any, List
import os
import json
import tempfile
import shutil
from datetime import datetime, timezone

from executor.interfaces import ExecutorServiceInterface
from core.logger import get_logger
from core.database import async_session_maker

logger = get_logger(__name__)


class ExecutorService(ExecutorServiceInterface):
    """执行引擎服务实现"""
    
    async def execute(self, execution_id: int) -> Dict[str, Any]:
        """执行测试"""
        from plan.repository import ExecutionRecordRepository
        from plan.repository import TestPlanRepository
        from testcase.repository import TestCaseRepository
        
        async with async_session_maker() as session:
            execution_repo = ExecutionRecordRepository(session)
            plan_repo = TestPlanRepository(session)
            case_repo = TestCaseRepository(session)
            
            # 获取执行记录
            execution = await execution_repo.get_by_id(execution_id)
            if not execution:
                raise ValueError(f"执行记录不存在: {execution_id}")
            
            # 更新状态为运行中
            execution.status = "running"
            execution.start_time = datetime.utcnow()
            await execution_repo.update(execution)
            
            try:
                # 获取计划
                plan = await plan_repo.get_by_id(execution.plan_id)
                if not plan:
                    raise ValueError(f"测试计划不存在: {execution.plan_id}")
                
                # 准备测试用例
                test_cases = await self.prepare_test_cases(plan.id)
                
                # 生成测试目录
                test_dir = tempfile.mkdtemp(prefix="test_run_")
                allure_dir = execution.allure_results_path
                
                # 确保allure目录存在
                os.makedirs(allure_dir, exist_ok=True)
                
                # 生成pytest文件
                await self.generate_pytest_files(test_cases, test_dir)
                
                # 运行pytest
                pytest_result = await self.run_pytest(test_dir, allure_dir)
                
                # 解析allure结果
                allure_result = await self.parse_allure_results(allure_dir)
                
                # 更新执行记录
                execution.status = "finished"
                execution.end_time = datetime.now(timezone.utc)
                execution.duration = int((execution.end_time - execution.start_time).total_seconds())
                execution.total_cases = allure_result.get("total", 0)
                execution.passed_cases = allure_result.get("passed", 0)
                execution.failed_cases = allure_result.get("failed", 0)
                execution.skipped_cases = allure_result.get("skipped", 0)
                execution.summary = allure_result
                
                await execution_repo.update(execution)
                
                # 清理临时文件
                shutil.rmtree(test_dir, ignore_errors=True)
                
                logger.info(f"测试执行完成: execution_id={execution_id}, passed={execution.passed_cases}, failed={execution.failed_cases}")
                
                return {
                    "execution_id": execution_id,
                    "status": "finished",
                    "total": execution.total_cases,
                    "passed": execution.passed_cases,
                    "failed": execution.failed_cases,
                    "duration": execution.duration
                }
                
            except Exception as e:
                # 更新执行记录为失败
                execution.status = "failed"
                execution.end_time = datetime.now(timezone.utc)
                execution.duration = int((execution.end_time - execution.start_time).total_seconds())
                execution.error_message = str(e)
                await execution_repo.update(execution)
                
                logger.error(f"测试执行失败: execution_id={execution_id}, error={str(e)}")
                
                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": str(e)
                }
    
    async def prepare_test_cases(self, plan_id: int) -> List[Dict[str, Any]]:
        """准备测试用例"""
        from plan.repository import TestPlanRepository
        from testcase.repository import TestCaseRepository, TestSuiteRepository
        
        async with async_session_maker() as session:
            plan_repo = TestPlanRepository(session)
            case_repo = TestCaseRepository(session)
            suite_repo = TestSuiteRepository(session)
            
            # 获取计划
            plan = await plan_repo.get_by_id(plan_id)
            if not plan:
                raise ValueError(f"测试计划不存在: {plan_id}")
            
            # 收集所有用例ID
            all_case_ids = set()
            
            # 从用例集中获取用例
            for suite_id in plan.suite_ids:
                suite = await suite_repo.get_by_id(suite_id)
                if suite:
                    all_case_ids.update(suite.case_ids)
            
            # 获取用例详情
            cases = await case_repo.get_by_ids(list(all_case_ids))
            
            # 转换为字典格式
            test_cases = []
            for case in cases:
                test_cases.append({
                    "id": case.id,
                    "name": case.name,
                    "method": case.method,
                    "url": case.url,
                    "headers": case.headers or {},
                    "params": case.params or {},
                    "body": case.body or {},
                    "assertions": case.assertions or [],
                    "extract": case.extract or [],
                    "timeout": case.timeout
                })
            
            return test_cases
    
    async def generate_pytest_files(self, test_cases: List[Dict[str, Any]], output_dir: str) -> str:
        """生成pytest测试文件"""
        # import yaml
        from ruamel.yaml import YAML

        # 创建 YAML 实例
        _yaml = YAML(typ='rt')
        _yaml.default_flow_style = False
        _yaml.allow_unicode = True
        _yaml.preserve_quotes = True
        _yaml.sort_keys = False

        # 生成conftest.py
        conftest_content = '''
            import pytest
            import allure
            import httpx
            import json
            
            @pytest.fixture
            def http_client():
                """HTTP客户端fixture"""
                with httpx.Client(timeout=30.0) as client:
                    yield client
            '''
        
        conftest_path = os.path.join(output_dir, "conftest.py")
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftest_content)
        
        # 生成测试文件
        test_content = ('''
            import pytest
            import allure
            import httpx
            import json
            
            # 测试用例数据
            TEST_CASES = {test_cases_data}
            
            @pytest.mark.parametrize("case", TEST_CASES, ids=[c["name"] for c in TEST_CASES])
            def test_api_case(case, http_client):
                """API测试用例"""
                with allure.step(f"执行测试: {case['name']}"):
                    # 发送请求
                    response = http_client.request(
                        method=case["method"],
                        url=case["url"],
                        headers=case.get("headers", {{}}),
                        params=case.get("params", {{}}),
                        json=case.get("body"),
                        timeout=case.get("timeout", 30)
                    )
                    
                    # 添加Allure附件
                    allure.attach(
                        json.dumps(case, ensure_ascii=False, indent=2),
                        name="请求信息",
                        attachment_type=allure.attachment_type.JSON
                    )
                    
                    allure.attach(
                        response.text,
                        name="响应内容",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    
                    # 执行断言
                    assertions = case.get("assertions", [])
                    for assertion in assertions:
                        assertion_type = assertion.get("type")
                        expected = assertion.get("expected")
                        
                        if assertion_type == "status_code":
                            assert response.status_code == expected, f"状态码断言失败: 期望 {{expected}}, 实际 {{response.status_code}}"
                        elif assertion_type == "response_time":
                            assert response.elapsed.total_seconds() < expected, f"响应时间断言失败: 期望 < {{expected}}s"
                        elif assertion_type == "json_path":
                            # TODO: 实现JSON路径断言
                            pass
            '''.format(test_cases_data=json.dumps(test_cases, ensure_ascii=False, indent=4)))
        
        test_path = os.path.join(output_dir, "test_api.py")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        return output_dir
    
    async def run_pytest(self, test_dir: str, allure_dir: str) -> Dict[str, Any]:
        """运行pytest"""
        import subprocess
        
        # 构建pytest命令
        cmd = [
            "pytest",
            test_dir,
            f"--alluredir={allure_dir}",
            "-v",
            "--tb=short"
        ]
        
        # 执行pytest
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    async def parse_allure_results(self, allure_dir: str) -> Dict[str, Any]:
        """解析Allure结果"""
        import glob
        
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        
        # 读取所有JSON结果文件
        result_files = glob.glob(os.path.join(allure_dir, "*-result.json"))
        
        for result_file in result_files:
            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)
                total += 1
                
                status = result_data.get("status")
                if status == "passed":
                    passed += 1
                elif status == "failed":
                    failed += 1
                elif status == "skipped":
                    skipped += 1
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(passed / total * 100, 2) if total > 0 else 0
        }
