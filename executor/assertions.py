"""
测试断言模块
"""
import re
from typing import Any, Dict, List, Union
from core.constants import AssertionType
from core.logger import log_error
from jsonpath_ng import parse


class AssertionEngine:
    """断言引擎"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def assert_all(
            self,
            response: Any,
            assertions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行所有断言
        Args:
            response: 响应对象
            assertions: 断言列表
        Returns:
            断言结果
        """
        self.results = []

        for assertion in assertions:
            try:
                result = self._execute_assertion(response, assertion)
                self.results.append(result)
            except Exception as e:
                self.results.append({
                    "type": assertion.get("type"),
                    "passed": False,
                    "error": str(e),
                })

        passed_count = sum(1 for r in self.results if r.get("passed"))

        return {
            "total": len(self.results),
            "passed": passed_count,
            "failed": len(self.results) - passed_count,
            "details": self.results,
        }

    def _execute_assertion(
            self,
            response: Any,
            assertion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个断言

        Args:
            response: 响应对象
            assertion: 断言配置

        Returns:
            断言结果
        """
        assertion_type = assertion.get("type")
        expected = assertion.get("expected")

        result = {
            "type": assertion_type,
            "expected": expected,
            "passed": False,
        }

        try:
            if assertion_type == AssertionType.STATUS_CODE:
                actual = response.status_code
                result["actual"] = actual
                result["passed"] = actual == expected

            elif assertion_type == AssertionType.RESPONSE_TIME:
                actual = response.elapsed.total_seconds()
                result["actual"] = actual
                result["passed"] = actual <= expected

            elif assertion_type == AssertionType.JSON_PATH:
                actual = self._extract_json_path(response, assertion.get("path"))
                result["actual"] = actual
                result["passed"] = self._compare(actual, expected, assertion.get("operator", "=="))

            elif assertion_type == AssertionType.BODY_CONTAINS:
                body = response.text
                result["actual"] = f"contains: {expected}"
                result["passed"] = expected in body

            elif assertion_type == AssertionType.HEADER:
                header_name = assertion.get("header")
                actual = response.headers.get(header_name)
                result["actual"] = actual
                result["passed"] = actual == expected

            elif assertion_type == AssertionType.CONTENT_TYPE:
                actual = response.headers.get("Content-Type", "")
                result["actual"] = actual
                result["passed"] = expected in actual

            else:
                result["error"] = f"不支持的断言类型: {assertion_type}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def _extract_json_path(
            self,
            response: Any,
            path: str
    ) -> Any:
        """
        从JSON响应中提取指定路径的值
        Args:
            response: 响应对象
            path: JSON路径 (如 $.data.id)
        Returns:
            提取的值
        """
        json_data = response.json()

        if not path.startswith("$"):
            path = f"$.{path}" if not path.startswith(".") else f"${path}"
        try:
            expr = parse(path)
            matches = [match.value for match in expr.find(json_data)]
            if matches:
                return matches[0]
            else:
                return None # 未找到匹配时，返回None
        except Exception as e:
            log_error(f"Invalid JSON path: {path}")
            raise ValueError(f"Invalid JSON path: {e}")

    def _compare(
            self,
            actual: Any,
            expected: Any,
            operator: str
    ) -> bool:
        """
        比较实际值和期望值
        Args:
            actual: 实际值
            expected: 期望值
            operator: 比较操作符
        Returns:
            比较结果
        """
        if operator == "==" or operator == "equals":
            return actual == expected
        elif operator == "!=" or operator == "not_equals":
            return actual != expected
        elif operator == ">" or operator == "greater_than":
            return actual > expected
        elif operator == ">=" or operator == "greater_or_equal":
            return actual >= expected
        elif operator == "<" or operator == "less_than":
            return actual < expected
        elif operator == "<=" or operator == "less_or_equal":
            return actual <= expected
        elif operator == "contains":
            return expected in actual
        elif operator == "not_contains":
            return expected not in actual
        elif operator == "regex":
            return bool(re.search(expected, str(actual)))
        else:
            return actual == expected


class JSONPathAssertion:
    """JSON路径断言"""

    @staticmethod
    def assert_value(
            json_data: Union[dict, list],
            path: str,
            expected: Any,
            operator: str = "=="
    ) -> Dict[str, Any]:
        """
        JSON路径断言
        Args:
            json_data: JSON数据
            path: JSON路径
            expected: 期望值
            operator: 比较操作符
        Returns:
            断言结果
        """
        # 标准化路径
        if not path.startswith('$'):
            path = f"$.{path}" if not path.startswith('.') else f"${path}"
        try:
            expr = parse(path)
            matches = [match.value for match in expr.find(json_data)]
            if not matches:
                return {
                    "passed": False,
                    "error": f"路径 {path} 未找到匹配值",
                }
            actual = matches[0]
        except Exception as e:
            return {
                "passed": False,
                "error": f"JSONPath 解析或执行错误: {str(e)}",
            }

        # 比较
        if operator == "==" or operator == "equals":
            passed = actual == expected
        elif operator == "!=" or operator == "not_equals":
            passed = actual != expected
        elif operator == ">" or operator == "greater_than":
            passed = actual > expected
        elif operator == ">=" or operator == "greater_or_equal":
            passed = actual >= expected
        elif operator == "<" or operator == "less_than":
            passed = actual < expected
        elif operator == "<=" or operator == "less_or_equal":
            passed = actual <= expected
        elif operator == "contains":
            passed = expected in actual
        elif operator == "regex":
            passed = bool(re.search(expected, str(actual)))
        else:
            passed = actual == expected

        return {
            "passed": passed,
            "path": path,
            "expected": expected,
            "actual": actual,
            "operator": operator,
        }


class ResponseAssertion:
    """响应断言"""

    @staticmethod
    def assert_status_code(response: Any, expected: int) -> Dict[str, Any]:
        """断言状态码"""
        actual = response.status_code
        return {
            "passed": actual == expected,
            "expected": expected,
            "actual": actual,
        }

    @staticmethod
    def assert_response_time(response: Any, max_seconds: float) -> Dict[str, Any]:
        """断言响应时间"""
        actual = response.elapsed.total_seconds()
        return {
            "passed": actual <= max_seconds,
            "expected": f"< {max_seconds}s",
            "actual": f"{actual:.3f}s",
        }

    @staticmethod
    def assert_body_contains(response: Any, text: str) -> Dict[str, Any]:
        """断言响应体包含文本"""
        body = response.text
        return {
            "passed": text in body,
            "expected": f"contains: {text}",
        }

    @staticmethod
    def assert_header(response: Any, header_name: str, expected: str) -> Dict[str, Any]:
        """断言响应头"""
        actual = response.headers.get(header_name)
        return {
            "passed": actual == expected,
            "header": header_name,
            "expected": expected,
            "actual": actual,
        }

    @staticmethod
    def assert_content_type(response: Any, expected: str) -> Dict[str, Any]:
        """断言Content-Type"""
        actual = response.headers.get("Content-Type", "")
        return {
            "passed": expected in actual,
            "expected": expected,
            "actual": actual,
        }


class SchemaAssertion:
    """JSON Schema断言"""

    @staticmethod
    def assert_schema(
            json_data: Union[dict, list],
            schema: dict
    ) -> Dict[str, Any]:
        """
        验证JSON数据是否符合Schema
        Args:
            json_data: JSON数据
            schema: JSON Schema
        Returns:
            验证结果
        """
        import jsonschema
        try:
            jsonschema.validate(instance=json_data, schema=schema)
            return {"passed": True}
        except jsonschema.ValidationError as e:
            return {
                "passed": False,
                "error": e.message,
                "path": list(e.absolute_path),
            }
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
            }
