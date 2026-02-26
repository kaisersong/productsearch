"""网页内容抓取工具，使用 BeautifulSoup 提取正文。"""

from typing import Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from product_search.core.exceptions import ScraperError
from product_search.core.logger import logger

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 跳过这些标签，减少噪音
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "advertisement"]

MAX_CONTENT_LENGTH = 8000  # 返回最多 8000 字符，节省 token


class WebScraper:
    """网页内容抓取器，提取主体文本。"""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def scrape(self, url: str) -> str:
        """抓取网页并返回清洗后的文本内容。

        Args:
            url: 目标 URL。

        Returns:
            提取的纯文本内容（截断至 MAX_CONTENT_LENGTH）。

        Raises:
            ScraperError: 抓取失败时抛出。
        """
        logger.debug(f"抓取网页: {url}")
        try:
            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            text = self._extract_text(html)
            logger.debug(f"抓取成功: {url}，提取 {len(text)} 字符")
            return text[:MAX_CONTENT_LENGTH]

        except httpx.TimeoutException:
            raise ScraperError(f"抓取超时: {url}")
        except httpx.HTTPStatusError as e:
            raise ScraperError(f"HTTP 错误 {e.response.status_code}: {url}")
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperError(f"抓取失败: {url} — {e}") from e

    def _extract_text(self, html: str) -> str:
        """从 HTML 中提取干净的正文文本。"""
        soup = BeautifulSoup(html, "html.parser")

        # 移除噪音标签
        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        # 优先尝试 main/article 内容区域
        main_content = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"})
        target = main_content if main_content else soup.body if soup.body else soup

        lines = []
        for element in target.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = element.get_text(separator=" ", strip=True)
            if len(text) > 20:  # 过滤过短片段
                lines.append(text)

        return "\n".join(lines)
