"""LangGraph StateGraph 工作流定义和编译。"""

import functools
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from product_search.core.config import config
from product_search.core.logger import logger
from product_search.graph.conditions import should_continue
from product_search.llm.factory import create_llm
from product_search.nodes.analyze_node import aggregate_results, format_output
from product_search.nodes.extract_node import extract_products, scrape_content
from product_search.nodes.search_node import generate_queries, web_search
from product_search.state.graph_state import ProductSearchState
from product_search.tools.product_extractor import ProductExtractor
from product_search.tools.web_scraper import WebScraper
from product_search.tools.web_search import WebSearchTool


def build_workflow(
    llm: Optional[BaseChatModel] = None,
    analysis_llm: Optional[BaseChatModel] = None,
    use_checkpointer: bool = True,
) -> "CompiledStateGraph":
    """构建并编译 ProductSearch LangGraph 工作流。

    Args:
        llm: 主要 LLM（用于查询生成和产品提取）。留空则从配置自动创建。
        analysis_llm: 分析步骤专用 LLM（可更强）。留空则复用 llm。
        use_checkpointer: 是否启用 MemorySaver（支持断点续跑）。

    Returns:
        编译好的 CompiledStateGraph。
    """
    logger.info("构建 ProductSearch 工作流...")

    # 初始化 LLM
    if llm is None:
        llm = create_llm("default")
    if analysis_llm is None:
        # 尝试使用 analysis 配置，失败则复用 default
        try:
            analysis_llm = create_llm("analysis")
        except Exception:
            analysis_llm = llm

    # 初始化工具
    search_tool = WebSearchTool()
    scraper = WebScraper()
    extractor = ProductExtractor(llm=llm)

    # 用 functools.partial 绑定依赖到节点函数
    generate_queries_node = functools.partial(generate_queries, llm=llm)
    web_search_node = functools.partial(web_search, search_tool=search_tool)
    scrape_content_node = functools.partial(scrape_content, scraper=scraper)
    extract_products_node = functools.partial(extract_products, extractor=extractor)
    format_output_node = functools.partial(format_output, llm=analysis_llm)

    # 构建 StateGraph
    graph = StateGraph(ProductSearchState)

    # 添加节点
    graph.add_node("generate_queries", generate_queries_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("scrape_content", scrape_content_node)
    graph.add_node("extract_products", extract_products_node)
    graph.add_node("aggregate_results", aggregate_results)
    graph.add_node("format_output", format_output_node)

    # 添加边（顺序执行）
    graph.add_edge(START, "generate_queries")
    graph.add_edge("generate_queries", "web_search")
    graph.add_edge("web_search", "scrape_content")
    graph.add_edge("scrape_content", "extract_products")

    # 条件边：判断是否继续迭代
    graph.add_conditional_edges(
        "extract_products",
        should_continue,
        {
            "continue": "generate_queries",    # 返回搜索循环
            "aggregate": "aggregate_results",  # 进入聚合分析
        },
    )

    graph.add_edge("aggregate_results", "format_output")
    graph.add_edge("format_output", END)

    # 编译
    checkpointer = MemorySaver() if use_checkpointer else None
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("工作流构建完成")
    return compiled


async def run_search(
    company_name: str,
    max_iterations: int = 3,
    llm: Optional[BaseChatModel] = None,
    analysis_llm: Optional[BaseChatModel] = None,
) -> ProductSearchState:
    """运行产品搜索工作流的便捷入口函数。

    Args:
        company_name: 目标企业名称。
        max_iterations: 最大搜索迭代次数（默认 3）。
        llm: 主要 LLM，留空从配置创建。
        analysis_llm: 分析 LLM，留空从配置创建或复用 llm。

    Returns:
        最终工作流状态（包含 products 和 summary）。
    """
    workflow = build_workflow(llm=llm, analysis_llm=analysis_llm)

    initial_state: ProductSearchState = {
        "company_name": company_name,
        "messages": [],
        "search_queries": [],
        "all_queries_used": [],
        "raw_search_results": [],
        "scraped_content": [],
        "scraped_urls": [],
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "should_continue": True,
        "products": [],
        "summary": None,
    }

    config_dict = {"configurable": {"thread_id": f"search_{company_name}"}}

    logger.info(f"开始搜索: company={company_name}, max_iterations={max_iterations}")
    final_state = await workflow.ainvoke(initial_state, config=config_dict)
    logger.info(f"搜索完成: 发现 {len(final_state.get('products', []))} 个产品")

    return final_state
