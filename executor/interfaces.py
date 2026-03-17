"""
执行引擎模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class ExecutorServiceInterface(ABC):
    """执行引擎服务接口"""
    
    @abstractmethod
    async def execute(self, execution_id: int) -> Dict[str, Any]:
        """执行测试"""
        pass
    
    @abstractmethod
    async def prepare_test_cases(self, plan_id: int) -> List[Dict[str, Any]]:
        """准备测试用例"""
        pass
    
    @abstractmethod
    async def generate_pytest_files(self, test_cases: List[Dict[str, Any]], output_dir: str) -> str:
        """生成pytest测试文件"""
        pass
    
    @abstractmethod
    async def run_pytest(self, test_dir: str, allure_dir: str) -> Dict[str, Any]:
        """运行pytest"""
        pass
    
    @abstractmethod
    async def parse_allure_results(self, allure_dir: str) -> Dict[str, Any]:
        """解析Allure结果"""
        pass
