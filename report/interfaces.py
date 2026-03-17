"""
报告模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ReportServiceInterface(ABC):
    """报告服务接口"""
    
    @abstractmethod
    async def generate_report(self, execution_id: int) -> Dict[str, Any]:
        """生成报告"""
        pass
    
    @abstractmethod
    async def get_report(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """获取报告"""
        pass
    
    @abstractmethod
    async def generate_allure_html(self, allure_dir: str, output_dir: str) -> str:
        """生成Allure HTML报告"""
        pass
    
    @abstractmethod
    async def archive_report(self, execution_id: int, report_dir: str) -> str:
        """归档报告"""
        pass
