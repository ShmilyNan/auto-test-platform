# -*- coding: utf-8 -*-
"""
YAML文件加载器
提供统一的YAML文件加载功能
"""
import logging
from pathlib import Path
from ruamel.yaml import YAML, YAMLError
from typing import Dict, Any, Union, List, Optional

# 创建 YAML 实例
_yaml = YAML(typ='rt')
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


class YAMLLoader:
    """YAML文件加载器"""

    def __init__(self, encoding: str = 'utf-8'):
        """
        初始化YAML加载器
        Args:
            encoding: 文件编码，默认 utf-8
        """
        self.encoding = encoding
        # 创建专用的 YAML 实例
        self.yaml = YAML(typ='safe')
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.preserve_quotes = True
        self.yaml.sort_keys = False

        # 使用标准 logging 记录日志
        self.logger = logging.getLogger(__name__)

    def load(
            self,
            file_path: Union[str, Path],
            default: Optional[Any] = None
    ) -> Any:
        """
        加载YAML文件
        Args:
            file_path: YAML文件路径（字符串或Path对象）
            default: 文件不存在或解析失败时的默认值
        Returns:
            Any: 解析后的数据，失败时返回默认值
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                self.logger.warning(f"YAML文件不存在: {file_path}")
                return default

            with open(file_path, 'r', encoding=self.encoding) as f:
                data = self.yaml.load(f)

            self.logger.debug(f"成功加载YAML文件: {file_path}")
            return data

        except YAMLError as e:
            self.logger.error(f"YAML解析错误: {file_path}, 错误: {str(e)}")
            return default
        except Exception as e:
            self.logger.error(f"加载YAML文件失败: {file_path}, 错误: {str(e)}")
            return default

    def load_or_raise(
            self,
            file_path: Union[str, Path]
    ) -> Any:
        """
        加载YAML文件，失败时抛出异常
        Args:
            file_path: YAML文件路径
        Returns:
            Any: 解析后的数据
        Raises:
            FileNotFoundError: 文件不存在
            YAMLError: YAML解析错误
            IOError: 文件读取错误
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"YAML文件不存在: {file_path}")

        try:
            with open(file_path, 'r', encoding=self.encoding) as f:
                data = self.yaml.load(f)

            self.logger.info(f"成功加载YAML文件: {file_path}")
            return data

        except YAMLError:
            self.logger.error(f"YAML解析错误: {file_path}")
            raise
        except IOError:
            self.logger.error(f"文件读取错误: {file_path}")
            raise

    def load_dict(
            self,
            file_path: Union[str, Path],
            default: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        加载YAML文件并返回字典类型
        Args:
            file_path: YAML文件路径
            default: 默认值（空字典）
        Returns:
            Dict: 解析后的字典数据
        """
        if default is None:
            default = {}

        data = self.load(file_path, default)

        if not isinstance(data, dict):
            self.logger.warning(f"YAML文件内容不是字典类型: {file_path}, 返回默认值")
            return default

        return data

    def load_list(
            self,
            file_path: Union[str, Path],
            default: Optional[List] = None
    ) -> List[Any]:
        """
        加载YAML文件并返回列表类型
        Args:
            file_path: YAML文件路径
            default: 默认值（空列表）
        Returns:
            List: 解析后的列表数据
        """
        if default is None:
            default = []

        data = self.load(file_path, default)

        if not isinstance(data, list):
            self.logger.warning(f"YAML文件内容不是列表类型: {file_path}, 返回默认值")
            return default

        return data

    def load_from_string(
            self,
            yaml_string: str,
            default: Optional[Any] = None
    ) -> Any:
        """
        从字符串加载YAML数据
        Args:
            yaml_string: YAML格式字符串
            default: 解析失败时的默认值
        Returns:
            Any: 解析后的数据
        """
        try:
            if not yaml_string or not yaml_string.strip():
                return default

            # 使用全局 YAML 实例从字符串加载
            data = _yaml.load(yaml_string)
            self.logger.debug("成功从字符串加载YAML数据")
            return data

        except YAMLError as e:
            self.logger.error(f"YAML字符串解析错误: {str(e)}")
            return default

    def save(
            self,
            data: Any,
            file_path: Union[str, Path],
            sort_keys: bool = False
    ) -> bool:
        """
        保存数据到YAML文件
        Args:
            data: 要保存的数据
            file_path: 目标文件路径
            sort_keys: 是否排序字典的键
        Returns:
            bool: 是否保存成功
        """
        try:
            file_path = Path(file_path)

            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 设置排序
            self.yaml.sort_keys = sort_keys

            with open(file_path, 'w', encoding=self.encoding) as f:
                self.yaml.dump(data, f)

            self.logger.info(f"成功保存YAML文件: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存YAML文件失败: {file_path}, 错误: {str(e)}")
            return False

    def load_with_validation(
            self,
            file_path: Union[str, Path],
            required_fields: Optional[List[str]] = None,
            default: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        加载YAML文件并验证必填字段
        Args:
            file_path: YAML文件路径
            required_fields: 必填字段列表
            default: 默认值（空字典）
        Returns:
            Dict: 解析后的字典数据
        """
        if default is None:
            default = {}

        if required_fields is None:
            required_fields = []

        data = self.load_dict(file_path, default)

        # 验证必填字段
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            self.logger.warning(
                f"YAML文件缺少必填字段: {file_path}, "
                f"缺失字段: {missing_fields}"
            )

        return data

    def load_multi(
            self,
            file_paths: List[Union[str, Path]],
            merge: bool = False
    ) -> Union[List[Any], Dict[str, Any]]:
        """
        批量加载多个YAML文件
        Args:
            file_paths: 文件路径列表
            merge: 是否合并所有文件的数据
        Returns:
            List或Dict: 加载的数据列表或合并后的字典
        """
        results = []

        for file_path in file_paths:
            data = self.load(file_path)
            if data is not None:
                results.append(data)

        if merge:
            # 合并所有字典
            merged = {}
            for data in results:
                if isinstance(data, dict):
                    merged.update(data)
            return merged

        return results

    def get_nested_value(
            self,
            data: Dict[str, Any],
            path: str,
            default: Any = None,
            separator: str = '.'
    ) -> Any:
        """
        从嵌套字典中获取值
        Args:
            data: 字典数据
            path: 嵌套路径，如 "config.database.host"
            default: 默认值
            separator: 路径分隔符
        Returns:
            Any: 获取的值
        """
        keys = path.split(separator)
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current


# 全局实例
_yaml_loader = None


def get_yaml_loader() -> YAMLLoader:
    """
    获取全局YAML加载器实例
    Returns:
        YAMLLoader: YAML加载器实例
    """
    global _yaml_loader

    if _yaml_loader is None:
        _yaml_loader = YAMLLoader()

    return _yaml_loader


# 便捷函数
def load_yaml(file_path: Union[str, Path], default: Any = None) -> Any:
    """
    便捷函数：加载YAML文件
    Args:
        file_path: YAML文件路径
        default: 默认值
    Returns:
        Any: 解析后的数据
    """
    return get_yaml_loader().load(file_path, default)


def load_yaml_dict(file_path: Union[str, Path], default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    便捷函数：加载YAML文件为字典
    Args:
        file_path: YAML文件路径
        default: 默认值
    Returns:
        Dict: 解析后的字典数据
    """
    return get_yaml_loader().load_dict(file_path, default)


def save_yaml(data: Any, file_path: Union[str, Path], sort_keys: bool = False) -> bool:
    """
    便捷函数：保存数据到YAML文件
    Args:
        data: 要保存的数据
        file_path: 目标文件路径
        sort_keys: 是否排序字典的键
    Returns:
        bool: 是否保存成功
    """
    return get_yaml_loader().save(data, file_path, sort_keys)
