"""工具层单元测试（无需 API Key）。"""

import pytest
from unittest.mock import AsyncMock, patch

from product_search.tools.product_extractor import ProductExtractor, ProductInfo
from product_search.tools.web_scraper import WebScraper
from product_search.tools.web_search import SearchResult, WebSearchTool


# ── ProductExtractor ──────────────────────────────────────────────────────────

class TestProductExtractor:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_returns_products(self, mock_llm):
        extractor = ProductExtractor(llm=mock_llm)
        products = await extractor.extract(
            content="华为 Mate 60 Pro 手机，华为 MateBook 笔记本电脑",
            company_name="华为",
            source_url="https://example.com",
        )
        assert len(products) == 2
        assert all(isinstance(p, ProductInfo) for p in products)
        assert products[0].name == "华为 Mate 60 Pro"
        assert products[0].category == "手机"
        assert products[0].confidence >= 0.6

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_empty_content_returns_empty(self, mock_llm):
        extractor = ProductExtractor(llm=mock_llm)
        # 空内容直接返回 []，不调用 LLM
        products = await extractor.extract(content="  ", company_name="华为")
        assert products == []
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.unit
    def test_parse_response_handles_markdown_code_block(self, mock_llm):
        extractor = ProductExtractor(llm=mock_llm)
        raw = '''```json
{"products": [{"name": "iPhone 15", "category": "手机", "confidence": 0.9}]}
```'''
        products = extractor._parse_response(raw, "https://apple.com")
        assert len(products) == 1
        assert products[0].name == "iPhone 15"

    @pytest.mark.unit
    def test_parse_response_handles_invalid_json(self, mock_llm):
        extractor = ProductExtractor(llm=mock_llm)
        products = extractor._parse_response("这不是JSON内容", "https://example.com")
        assert products == []

    @pytest.mark.unit
    def test_parse_response_fills_source_url(self, mock_llm):
        extractor = ProductExtractor(llm=mock_llm)
        raw = '{"products": [{"name": "Test", "category": "电子", "confidence": 0.8}]}'
        products = extractor._parse_response(raw, "https://test.com")
        assert products[0].source_url == "https://test.com"


# ── WebScraper ────────────────────────────────────────────────────────────────

class TestWebScraper:
    @pytest.mark.unit
    def test_extract_text_from_html(self):
        scraper = WebScraper()
        html = """<html><body>
            <script>alert('噪音')</script>
            <nav>导航栏噪音</nav>
            <main>
                <h1>华为产品线介绍及其最新发布情况</h1>
                <p>华为手机 Mate 系列是旗舰产品线，代表华为最高技术水准。</p>
                <p>华为笔记本 MateBook 系列专注于高效办公。</p>
            </main>
        </body></html>"""
        text = scraper._extract_text(html)
        assert "Mate 系列" in text          # p 标签内容足够长，应被提取
        assert "MateBook 系列" in text
        assert "alert" not in text          # script 内容被过滤

    @pytest.mark.unit
    def test_extract_text_filters_short_lines(self):
        scraper = WebScraper()
        html = "<html><body><p>短</p><p>这是一段足够长的内容，应该被包含进来，超过20个字符</p></body></html>"
        text = scraper._extract_text(html)
        assert "短" not in text
        assert "足够长" in text


# ── WebSearchTool ─────────────────────────────────────────────────────────────

class TestWebSearchTool:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_search_tool):
        results = await mock_search_tool.search("华为产品", max_results=5)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.unit
    def test_unsupported_engine_raises(self):
        from product_search.core.config import SearchSettings
        settings = SearchSettings(engine="unknown_engine")
        tool = WebSearchTool(settings=settings)
        import asyncio
        from product_search.core.exceptions import SearchError
        with pytest.raises(SearchError, match="不支持的搜索引擎"):
            asyncio.get_event_loop().run_until_complete(tool.search("test"))


# ── ProductInfo ───────────────────────────────────────────────────────────────

class TestProductInfo:
    @pytest.mark.unit
    def test_product_info_validation(self):
        p = ProductInfo(name="iPhone 15", category="手机", confidence=0.9)
        assert p.name == "iPhone 15"
        assert p.category == "手机"
        assert p.confidence == 0.9

    @pytest.mark.unit
    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ProductInfo(name="Test", category="测试", confidence=1.5)  # 超出范围

    @pytest.mark.unit
    def test_default_values(self):
        p = ProductInfo(name="Test", category="测试")
        assert p.description == ""
        assert p.source_url == ""
        assert p.confidence == 0.8
