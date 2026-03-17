"""
统计模块接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class StatsServiceInterface(ABC):
    """统计服务接口"""
    
    @abstractmethod
    async def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目统计"""
        pass
    
    @abstractmethod
    async def get_execution_trend(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取执行趋势"""
        pass
    
    @abstractmethod
    async def get_pass_rate_trend(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取通过率趋势"""
        pass
    
    @abstractmethod
    async def get_case_stats(self, project_id: int) -> Dict[str, Any]:
        """获取用例统计"""
        pass
    
    @abstractmethod
    async def get_duration_stats(self, project_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取执行时长统计"""
        pass
