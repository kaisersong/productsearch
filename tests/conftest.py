"""共用测试 fixtures，提供 mock LLM 和 mock 搜索工具。"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

from product_search.tools.product_extractor import ProductInfo
from product_search.tools.web_search import SearchResult


@pytest.fixture
def mock_llm():
    """Mock LLM，返回预设的产品 JSON 响应。"""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content='''{
  "products": [
    {
      "name": "华为 Mate 60 Pro",
      "category": "手机",
      "description": "华为旗舰智能手机",
      "source_url": "https://example.com",
      "confidence": 0.95
    },
    {
      "name": "华为 MateBook X Pro",
      "category": "笔记本电脑",
      "description": "华为轻薄笔记本",
      "source_url": "https://example.com",
      "confidence": 0.9
    }
  ]
}'''))
    return llm


@pytest.fixture
def mock_search_tool():
    """Mock 搜索工具，返回固定的搜索结果。"""
    tool = AsyncMock()
    tool.search = AsyncMock(return_value=[
        SearchResult(
            title="华为官方产品页",
            url="https://consumer.huawei.com/cn/phones/",
            snippet="华为手机、平板、笔记本、穿戴设备等消费电子产品",
        ),
        SearchResult(
            title="华为企业产品",
            url="https://e.huawei.com/cn/products/",
            snippet="华为企业级服务器、存储、网络设备",
        ),
    ])
    return tool


@pytest.fixture
def mock_scraper():
    """Mock 网页抓取器，返回固定的文本内容。"""
    scraper = AsyncMock()
    scraper.scrape = AsyncMock(return_value=(
        "华为手机 Mate 60 Pro，搭载麒麟芯片。"
        "华为笔记本 MateBook X Pro，轻薄旗舰。"
        "华为平板 MatePad Pro，专业创作。"
    ))
    return scraper


@pytest.fixture
def sample_products():
    """示例产品列表 fixture。"""
    return [
        ProductInfo(name="华为 Mate 60 Pro", category="手机", description="旗舰手机", confidence=0.95),
        ProductInfo(name="华为 MateBook X Pro", category="笔记本", description="旗舰本", confidence=0.9),
        ProductInfo(name="华为 MatePad Pro", category="平板", description="专业平板", confidence=0.85),
    ]


@pytest.fixture
def base_state():
    """最小化工作流初始状态 fixture。"""
    return {
        "company_name": "华为",
        "messages": [],
        "search_queries": [],
        "all_queries_used": [],
        "raw_search_results": [],
        "scraped_content": [],
        "scraped_urls": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "should_continue": True,
        "products": [],
        "summary": None,
    }
