"""
YAML测试文件解析器
"""
import os
from typing import List, Dict, Any
from pathlib import Path
from core.logger import logger
from ruamel.yaml import YAML

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


class YAMLParser:
    """YAML测试文件解析器"""

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析YAML测试文件
        Args:
            file_path: YAML文件路径
        Returns:
            测试用例列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = _yaml.load(f)

        if not content:
            return []

        # 支持多种格式
        test_cases = []

        # 格式1: 直接是测试用例列表
        if isinstance(content, list):
            test_cases = [self._parse_case(case, index) for index, case in enumerate(content)]

        # 格式2: 包含test_cases字段的字典
        elif isinstance(content, dict) and 'test_cases' in content:
            test_cases = [self._parse_case(case, index) for index, case in enumerate(content['test_cases'])]

        # 格式3: 单个测试用例
        elif isinstance(content, dict) and 'name' in content:
            test_cases = [self._parse_case(content, 0)]

        else:
            raise ValueError(f"不支持的YAML格式: {file_path}")

        logger.info(f"解析YAML文件成功: {file_path}, 共 {len(test_cases)} 个用例")
        return test_cases

    def parse_string(self, yaml_content: str) -> List[Dict[str, Any]]:
        """
        解析YAML字符串
        Args:
            yaml_content: YAML内容字符串
        Returns:
            测试用例列表
        """
        content = _yaml.load(yaml_content)

        if not content:
            return []

        if isinstance(content, list):
            return [self._parse_case(case, index) for index, case in enumerate(content)]
        elif isinstance(content, dict) and 'test_cases' in content:
            return [self._parse_case(case, index) for index, case in enumerate(content['test_cases'])]
        elif isinstance(content, dict) and 'name' in content:
            return [self._parse_case(content, 0)]
        else:
            raise ValueError("不支持的YAML格式")

    def _parse_case(self, case_data: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        解析单个测试用例
        Args:
            case_data: 用例数据
            index: 用例索引
        Returns:
            标准化的测试用例
        """
        # 标准化用例格式
        parsed_case = {
            "name": case_data.get("name", f"test_case_{index}"),
            "description": case_data.get("description", ""),
            "priority": case_data.get("priority", "medium"),
            "tags": case_data.get("tags", []),
            "request": self._parse_request(case_data.get("request", {})),
            "assertions": self._parse_assertions(case_data.get("assertions", [])),
            "variables": case_data.get("variables", {}),
            "setup": case_data.get("setup", []),
            "teardown": case_data.get("teardown", []),
        }

        return parsed_case

    def _parse_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析请求配置
        Args:
            request_data: 请求数据
        Returns:
            标准化的请求配置
        """
        if not request_data:
            return {}

        return {
            "method": request_data.get("method", "GET").upper(),
            "url": request_data.get("url", ""),
            "path": request_data.get("path", ""),
            "headers": request_data.get("headers", {}),
            "params": request_data.get("params", {}),
            "body": request_data.get("body"),
            "json": request_data.get("json"),
            "timeout": request_data.get("timeout", 30),
            "verify_ssl": request_data.get("verify_ssl", True),
        }

    def _parse_assertions(self, assertions: List[Any]) -> List[Dict[str, Any]]:
        """
        解析断言配置
        Args:
            assertions: 断言列表
        Returns:
            标准化的断言列表
        """
        parsed_assertions = []

        for assertion in assertions:
            # 支持简写格式: {"status_code": 200}
            if isinstance(assertion, dict):
                for key, value in assertion.items():
                    if key in ["status_code", "response_time", "json_path", "body_contains"]:
                        parsed_assertions.append({
                            "type": key,
                            "expected": value,
                            "path": assertion.get("path"),
                        })
                        break
                    else:
                        # 完整格式
                        parsed_assertions.append({
                            "type": assertion.get("type", key),
                            "expected": assertion.get("expected", value),
                            "path": assertion.get("path"),
                        })
                        break

        return parsed_assertions

    def parse_directory(self, directory: str, recursive: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析目录下的所有YAML测试文件
        Args:
            directory: 目录路径
            recursive: 是否递归解析子目录
        Returns:
            文件名到测试用例列表的映射
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")

        result = {}
        path = Path(directory)

        # 查找YAML文件
        if recursive:
            yaml_files = list(path.rglob("*.yaml")) + list(path.rglob("*.yml"))
        else:
            yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                test_cases = self.parse_file(str(yaml_file))
                result[yaml_file.name] = test_cases
            except Exception as e:
                logger.error(f"解析文件失败: {yaml_file}, 错误: {e}")

        logger.info(f"解析目录成功: {directory}, 共 {len(result)} 个文件")
        return result


def validate_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    验证YAML文件格式
    Args:
        file_path: YAML文件路径
    Returns:
        验证结果
    """
    parser = YAMLParser()

    try:
        test_cases = parser.parse_file(file_path)

        errors = []
        warnings = []

        for index, case in enumerate(test_cases):
            # 检查必填字段
            if not case.get("name"):
                errors.append(f"用例 {index}: 缺少name字段")

            if not case.get("request", {}).get("url") and not case.get("request", {}).get("path"):
                errors.append(f"用例 {case.get('name', index)}: 缺少url或path字段")

            # 检查建议字段
            if not case.get("assertions"):
                warnings.append(f"用例 {case.get('name', index)}: 没有断言")

        return {
            "valid": len(errors) == 0,
            "test_cases_count": len(test_cases),
            "errors": errors,
            "warnings": warnings,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
        }
