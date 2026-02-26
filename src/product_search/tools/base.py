"""工具基类，封装 LangChain BaseTool。"""

from abc import abstractmethod
from typing import Any, Optional

from langchain_core.tools import BaseTool as LCBaseTool
from pydantic import BaseModel

from product_search.core.logger import logger


class ToolResult(BaseModel):
    """工具执行结果。"""

    output: Any = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def __str__(self) -> str:
        return f"Error: {self.error}" if self.error else str(self.output)


class ProductSearchBaseTool(LCBaseTool):
    """ProductSearch 工具基类，统一日志和错误处理。"""

    name: str
    description: str

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        logger.debug(f"[{self.name}] 同步调用，参数: args={args}, kwargs={kwargs}")
        raise NotImplementedError("请使用异步方法 _arun")

    @abstractmethod
    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """异步执行工具。"""
