"""搜索节点：生成查询词 + 执行网络搜索。"""

import asyncio
from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from product_search.core.exceptions import SearchError
from product_search.core.logger import logger
from product_search.state.graph_state import ProductSearchState
from product_search.tools.web_search import SearchResult, WebSearchTool

QUERY_GENERATION_PROMPT = """你是一个专业的产品调研助手。

任务：为搜索"{company_name}"的产品信息生成搜索查询词。

要求：
1. 生成 3-5 个不同角度的查询词
2. 查询词要具体、有针对性
3. 避免重复已使用过的查询：{used_queries}
4. 用换行分隔，每行一个查询词，不要编号或其他格式

示例（针对"示例科技"）：
示例科技手机产品线 2024
示例科技笔记本电脑系列
示例科技平板电脑产品
示例科技企业网络设备
示例科技智能穿戴设备"""


async def generate_queries(state: ProductSearchState, llm: BaseChatModel) -> dict:
    """使用 LLM 生成多样化的搜索查询词。"""
    company_name = state["company_name"]
    used = state.get("all_queries_used", [])
    iteration = state.get("iteration_count", 0)

    logger.info(f"[search_node] 生成查询词 (迭代 {iteration + 1}): company={company_name}")

    prompt = QUERY_GENERATION_PROMPT.format(
        company_name=company_name,
        used_queries=", ".join(used) if used else "无",
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content="你是专业产品调研助手，擅长生成精准搜索查询词。"),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        queries = [q.strip() for q in raw.split("\n") if q.strip()]
        # 过滤已用过的
        new_queries = [q for q in queries if q not in used][:5]
    except Exception as e:
        logger.warning(f"LLM 生成查询词失败，使用默认查询: {e}")
        new_queries = [f"{company_name} 产品", f"{company_name} products"]

    logger.debug(f"生成查询词: {new_queries}")

    return {
        "search_queries": new_queries,
        "messages": [AIMessage(content=f"生成搜索查询词: {new_queries}")],
    }


async def web_search(state: ProductSearchState, search_tool: WebSearchTool) -> dict:
    """并发执行所有查询词的搜索。"""
    queries = state.get("search_queries", [])
    used = state.get("all_queries_used", [])
    max_results_per_query = 5  # 每个查询最多取 5 条

    logger.info(f"[search_node] 执行搜索: {len(queries)} 个查询词")

    # 并发搜索所有查询词
    tasks = [search_tool.search(q, max_results=max_results_per_query) for q in queries]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    all_results: List[SearchResult] = []
    existing_urls = {r.url for r in state.get("raw_search_results", [])}

    for query, results in zip(queries, results_list):
        if isinstance(results, Exception):
            logger.warning(f"查询失败: {query!r} — {results}")
            continue
        for r in results:
            if r.url and r.url not in existing_urls:
                all_results.append(r)
                existing_urls.add(r.url)

    logger.info(f"[search_node] 获取到 {len(all_results)} 条新结果")

    return {
        "raw_search_results": all_results,
        "all_queries_used": used + queries,
        "messages": [AIMessage(content=f"搜索完成，获取 {len(all_results)} 条新结果")],
    }
