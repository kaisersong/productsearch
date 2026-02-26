"""提取节点：抓取网页内容并提取结构化产品信息。"""

import asyncio
from typing import List

from langchain_core.messages import AIMessage

from product_search.core.logger import logger
from product_search.state.graph_state import ProductSearchState
from product_search.tools.product_extractor import ProductExtractor, ProductInfo
from product_search.tools.web_scraper import WebScraper
from product_search.tools.web_search import SearchResult

MAX_URLS_PER_ITERATION = 5   # 每轮最多抓取的 URL 数量
MIN_CONFIDENCE = 0.6          # 低于此置信度的产品被过滤


async def scrape_content(state: ProductSearchState, scraper: WebScraper) -> dict:
    """并发抓取搜索结果中的网页内容。"""
    results: List[SearchResult] = state.get("raw_search_results", [])
    already_scraped: List[str] = state.get("scraped_urls", [])

    # 选出未抓取的 URL
    new_results = [r for r in results if r.url not in already_scraped][:MAX_URLS_PER_ITERATION]

    if not new_results:
        logger.info("[extract_node] 没有新 URL 需要抓取")
        return {"scraped_content": [], "scraped_urls": already_scraped}

    logger.info(f"[extract_node] 并发抓取 {len(new_results)} 个 URL")

    tasks = [scraper.scrape(r.url) for r in new_results]
    contents = await asyncio.gather(*tasks, return_exceptions=True)

    scraped_content = []
    scraped_urls = list(already_scraped)
    url_content_pairs = []

    for result, content in zip(new_results, contents):
        if isinstance(content, Exception):
            logger.warning(f"抓取失败: {result.url} — {content}")
            scraped_urls.append(result.url)  # 标记为已尝试
        else:
            scraped_content.append(content)
            scraped_urls.append(result.url)
            url_content_pairs.append((result.url, content))

    logger.info(f"[extract_node] 成功抓取 {len(scraped_content)} 个页面")

    # 将 URL-content 对存入状态（通过自定义字段传递给 extract_products）
    return {
        "scraped_content": scraped_content,
        "scraped_urls": scraped_urls,
        # 临时字段：传递给下一步使用
        "_url_content_pairs": url_content_pairs,
    }


async def extract_products(state: ProductSearchState, extractor: ProductExtractor) -> dict:
    """从抓取的内容中并发提取产品信息。"""
    company_name = state["company_name"]
    url_content_pairs = state.get("_url_content_pairs", [])
    existing_products: List[ProductInfo] = state.get("products", [])

    if not url_content_pairs:
        # 回退：使用搜索 snippet 作为内容
        results = state.get("raw_search_results", [])
        scraped_urls = state.get("scraped_urls", [])
        url_content_pairs = [
            (r.url, f"{r.title}\n{r.snippet}")
            for r in results
            if r.url in scraped_urls and r.snippet
        ]

    if not url_content_pairs:
        logger.info("[extract_node] 无内容可提取")
        return {"products": existing_products, "should_continue": False}

    logger.info(f"[extract_node] 从 {len(url_content_pairs)} 个内容中提取产品")

    tasks = [
        extractor.extract(content, company_name, url)
        for url, content in url_content_pairs
    ]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # 合并去重
    existing_names = {p.name.lower() for p in existing_products}
    new_products: List[ProductInfo] = []

    for result in results_list:
        if isinstance(result, Exception):
            logger.warning(f"产品提取异常: {result}")
            continue
        for product in result:
            if product.confidence >= MIN_CONFIDENCE and product.name.lower() not in existing_names:
                new_products.append(product)
                existing_names.add(product.name.lower())

    all_products = existing_products + new_products
    logger.info(f"[extract_node] 新增 {len(new_products)} 个产品，累计 {len(all_products)} 个")

    iteration = state.get("iteration_count", 0) + 1
    max_iter = state.get("max_iterations", 3)

    return {
        "products": all_products,
        "iteration_count": iteration,
        "should_continue": iteration < max_iter and len(new_products) > 0,
        "messages": [AIMessage(content=f"第 {iteration} 轮提取完成，新增 {len(new_products)} 个产品，累计 {len(all_products)} 个")],
    }
