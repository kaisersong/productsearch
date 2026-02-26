"""多引擎网络搜索工具，支持 DuckDuckGo / SerpAPI / Serper。"""

from dataclasses import dataclass
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from product_search.core.config import SearchSettings, config
from product_search.core.exceptions import SearchError
from product_search.core.logger import logger


@dataclass
class SearchResult:
    """单条搜索结果。"""

    title: str
    url: str
    snippet: str


class WebSearchTool:
    """多引擎搜索工具，通过配置切换后端。

    参考 MetaGPT search_engine.py 的策略模式设计。
    """

    def __init__(self, settings: Optional[SearchSettings] = None):
        self.settings = settings or config.search
        self._engine_name = self.settings.engine.lower()
        logger.info(f"初始化搜索引擎: {self._engine_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """执行搜索，返回结构化结果列表。

        Args:
            query: 搜索查询词。
            max_results: 最大返回数，默认从配置读取。

        Returns:
            SearchResult 列表。

        Raises:
            SearchError: 搜索失败时抛出。
        """
        n = max_results or self.settings.max_results
        logger.debug(f"搜索: engine={self._engine_name}, query={query!r}, max_results={n}")

        try:
            if self._engine_name == "duckduckgo":
                return await self._search_duckduckgo(query, n)
            elif self._engine_name == "serpapi":
                return await self._search_serpapi(query, n)
            elif self._engine_name == "serper":
                return await self._search_serper(query, n)
            else:
                raise SearchError(f"不支持的搜索引擎: {self._engine_name}")
        except SearchError:
            raise
        except Exception as e:
            raise SearchError(f"搜索失败: {e}") from e

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:
            raise SearchError("请安装 ddgs: pip install ddgs")

        import asyncio

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: list(DDGS().text(query, max_results=max_results))
        )

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in results
        ]

    async def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        api_key = self.settings.effective_api_key()
        if not api_key:
            raise SearchError("SerpAPI Key 未配置。请设置 SERPAPI_API_KEY 环境变量。")

        import asyncio
        import httpx

        params = {
            "q": query,
            "api_key": api_key,
            "num": max_results,
            "engine": "google",
        }

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            ))
        return results

    async def _search_serper(self, query: str, max_results: int) -> List[SearchResult]:
        api_key = self.settings.effective_api_key()
        if not api_key:
            raise SearchError("Serper API Key 未配置。请设置 SERPER_API_KEY 环境变量。")

        import httpx

        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": max_results}

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            resp = await client.post("https://google.serper.dev/search", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            ))
        return results
