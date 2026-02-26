"""LangGraph 工作流状态定义。"""

from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from product_search.tools.product_extractor import ProductInfo
from product_search.tools.web_search import SearchResult


class ProductSearchState(TypedDict):
    """ProductSearch 工作流的完整状态。

    使用 TypedDict 定义，符合 LangGraph 规范。
    messages 字段使用 add_messages reducer，支持消息累加。
    """

    # 输入
    company_name: str

    # 消息历史（使用 add_messages reducer 累加）
    messages: Annotated[List[BaseMessage], add_messages]

    # 搜索相关
    search_queries: List[str]               # 本轮生成的搜索查询词
    all_queries_used: List[str]             # 历史所有使用过的查询词（用于去重）
    raw_search_results: List[SearchResult]  # 原始搜索结果

    # 抓取和提取
    scraped_content: List[str]              # 抓取的网页内容
    scraped_urls: List[str]                 # 已抓取 URL（去重）

    # 迭代控制
    iteration_count: int                    # 当前迭代次数
    max_iterations: int                     # 最大迭代次数
    should_continue: bool                   # 是否继续搜索

    # 结果
    products: List[ProductInfo]             # 已发现的产品（跨迭代累积）
    summary: Optional[str]                  # 最终汇总描述
