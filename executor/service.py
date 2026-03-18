"""
测试执行引擎服务层
"""
import os
import json
import tempfile
import shutil
import httpx
import textwrap
from string import Template
from typing import Dict, Any, List, Union
from datetime import datetime, timezone
from executor.assertions import AssertionEngine
from executor.interfaces import ExecutorServiceInterface
from core.logger import *
from core.database import async_session_maker


class ExecutorService(ExecutorServiceInterface):
    """执行引擎服务实现"""

    async def execute_single_case(
            self,
            case: Union[Dict[str, Any], Any]
    ) -> Dict[str, Any]:
        """
        执行单个测试用例

        Args:
            case: 测试用例，可以是字典或数据库模型对象

        Returns:
            执行结果字典，包含status、response、assertions等
        """
        # 标准化用例数据
        if hasattr(case, '__dict__'):
            # 数据库模型对象
            case_data = {
                "id": getattr(case, 'id', None),
                "name": getattr(case, 'name', 'Unknown'),
                "method": getattr(case, 'method', 'GET'),
                "url": getattr(case, 'url', ''),
                "headers": getattr(case, 'headers', {}) or {},
                "params": getattr(case, 'params', {}) or {},
                "body": getattr(case, 'body'),
                "assertions": getattr(case, 'assertions', []) or [],
                "timeout": getattr(case, 'timeout', 30),
            }
        else:
            # 字典对象
            case_data = case

        case_id = case_data.get("id")
        case_name = case_data.get("name", "Unknown")

        logger.info(f"执行测试用例: {case_name}")

        result = {
            "case_id": case_id,
            "case_name": case_name,
            "status": "pending",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "request": None,
            "response": None,
            "assertions": [],
            "error": None,
        }

        try:
            # 准备请求参数
            method = case_data.get("method", "GET").upper()
            url = case_data.get("url", "")
            headers = case_data.get("headers", {})
            params = case_data.get("params", {})
            body = case_data.get("body")
            timeout = case_data.get("timeout", 30)

            # 记录请求信息
            result["request"] = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "body": body,
            }

            # 发送HTTP请求
            async with httpx.AsyncClient(timeout=timeout) as client:
                request_kwargs = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "params": params,
                }

                # 根据方法决定是否发送body
                if method in ["POST", "PUT", "PATCH"] and body:
                    if isinstance(body, dict):
                        request_kwargs["json"] = body
                    else:
                        request_kwargs["content"] = body

                response = await client.request(**request_kwargs)

            # 记录响应信息
            result["response"] = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "elapsed_ms": response.elapsed.total_seconds() * 1000,
            }

            # 执行断言
            assertions = case_data.get("assertions", [])
            if assertions:
                assertion_engine = AssertionEngine()
                assertion_result = assertion_engine.assert_all(response, assertions)

                result["assertions"] = assertion_result.get("details", [])

                # 判断用例是否通过
                if assertion_result.get("failed", 0) > 0:
                    result["status"] = "failed"
                else:
                    result["status"] = "passed"
            else:
                # 没有断言，默认为通过
                result["status"] = "passed"

            logger.info(f"用例执行完成: {case_name}, 状态: {result['status']}")

        except httpx.TimeoutException as e:
            result["status"] = "failed"
            result["error"] = f"请求超时: {str(e)}"
            logger.error(f"用例执行超时: {case_name}, 错误: {e}")

        except httpx.RequestError as e:
            result["status"] = "failed"
            result["error"] = f"请求错误: {str(e)}"
            logger.error(f"用例执行请求错误: {case_name}, 错误: {e}")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"执行异常: {str(e)}"
            logger.error(f"用例执行异常: {case_name}, 错误: {e}", exc_info=True)

        result["end_time"] = datetime.now(timezone.utc).isoformat()

        return result

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
            execution.start_time = datetime.now(timezone.utc)
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

                # 解析并持久化用例级执行结果
                execution_results = await self.parse_test_case_results(allure_dir)
                await self.save_execution_results(execution_id, execution_results)

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

                log_info(f"测试执行完成: execution_id={execution_id}, passed={execution.passed_cases}, failed={execution.failed_cases}")

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

                log_error(f"测试执行失败: execution_id={execution_id}, error={str(e)}")

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

        # 生成conftest.py
        conftest_content = textwrap.dedent(
            '''
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
        )

        conftest_path = os.path.join(output_dir, "conftest.py")
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftest_content)

        # 生成测试文件
        test_template = Template(
            textwrap.dedent(
                '''
                import pytest
                import allure
                import httpx
                import json

                # 测试用例数据
                TEST_CASES = $test_cases_data

                @pytest.mark.parametrize("case", TEST_CASES, ids=[c["name"] for c in TEST_CASES])
                def test_api_case(case, http_client):
                    """API测试用例"""
                    with allure.step(f"执行测试: {case['name']}"):
                        # 发送请求
                        response = http_client.request(
                            method=case["method"],
                            url=case["url"],
                            headers=case.get("headers", {}),
                            params=case.get("params", {}),
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
                                assert response.status_code == expected, f"状态码断言失败: 期望 {expected}, 实际 {response.status_code}"
                            elif assertion_type == "response_time":
                                assert response.elapsed.total_seconds() < expected, f"响应时间断言失败: 期望 < {expected}s"
                            elif assertion_type == "json_path":
                                # JSON路径断言
                                json_path = assertion.get("path")

                                # 使用jsonpath解析响应
                                try:
                                    import jsonpath
                                    json_data = response.json()
                                    values = jsonpath.jsonpath(json_data, json_path)

                                    if values:
                                        actual = values[0]
                                        assert actual == expected, f"JSON路径断言失败: 路径 {json_path}, 期望 {expected}, 实际 {actual}"
                                    else:
                                        raise AssertionError(f"JSON路径断言失败: 路径 {json_path} 未找到匹配值")
                                except ImportError:
                                    # 简化实现：直接访问嵌套字典
                                    keys = json_path.replace("$$.", "").split(".")
                                    actual = response.json()
                                    for key in keys:
                                        if isinstance(actual, dict):
                                            actual = actual.get(key)
                                        else:
                                            raise AssertionError(f"JSON路径断言失败: 无法访问路径 {json_path}")

                                    assert actual == expected, f"JSON路径断言失败: 路径 {json_path}, 期望 {expected}, 实际 {actual}"
                '''
            )
        )
        test_content = test_template.substitute(
            test_cases_data=json.dumps(test_cases, ensure_ascii=False, indent=4)
        )
        
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

    async def parse_test_case_results(self, allure_dir: str) -> List[Dict[str, Any]]:
        """解析Allure结果中的用例级请求/响应详情"""
        import glob

        execution_results: List[Dict[str, Any]] = []
        result_files = glob.glob(os.path.join(allure_dir, "*-result.json"))

        for result_file in result_files:
            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            attachments = {
                attachment.get("name"): attachment
                for attachment in result_data.get("attachments", [])
                if attachment.get("name")
            }

            request_payload = self._load_allure_attachment(allure_dir, attachments.get("请求信息"))
            response_payload = self._load_allure_attachment(allure_dir, attachments.get("响应信息"))
            status_details = result_data.get("statusDetails") or {}
            start_time = result_data.get("start")
            stop_time = result_data.get("stop")

            execution_results.append(
                {
                    "case_id": request_payload.get("id") if isinstance(request_payload, dict) else None,
                    "case_name": result_data.get("name", "Unknown"),
                    "status": result_data.get("status", "unknown"),
                    "duration": int(stop_time - start_time) if start_time and stop_time else None,
                    "request": request_payload if isinstance(request_payload, dict) else None,
                    "response": response_payload if isinstance(response_payload, dict) else None,
                    "assertions": request_payload.get("assertions") if isinstance(request_payload, dict) else None,
                    "error_message": status_details.get("message"),
                    "stack_trace": status_details.get("trace"),
                }
            )

        return execution_results

    def _load_allure_attachment(self, allure_dir: str, attachment: Dict[str, Any] | None) -> Any:
        """读取Allure附件内容"""
        if not attachment:
            return None

        source = attachment.get("source")
        if not source:
            return None

        attachment_path = os.path.join(allure_dir, source)
        if not os.path.exists(attachment_path):
            return None

        with open(attachment_path, "r", encoding="utf-8") as f:
            content = f.read()

        attachment_type = attachment.get("type", "")
        if "json" in attachment_type.lower():
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"raw": content}

        return {"raw": content}

    async def save_execution_results(self, execution_id: int, execution_results: List[Dict[str, Any]]) -> None:
        """持久化用例级执行结果"""
        from plan.models import ExecutionResult
        from plan.repository import ExecutionResultRepository

        if not execution_results:
            return

        async with async_session_maker() as session:
            result_repo = ExecutionResultRepository(session)
            records = [
                ExecutionResult(
                    execution_id=execution_id,
                    case_id=result.get("case_id"),
                    case_name=result.get("case_name", "Unknown"),
                    status=result.get("status", "unknown"),
                    duration=result.get("duration"),
                    request=result.get("request"),
                    response=result.get("response"),
                    assertions=result.get("assertions"),
                    error_message=result.get("error_message"),
                    stack_trace=result.get("stack_trace"),
                )
                for result in execution_results
            ]
            await result_repo.create_batch(records)
