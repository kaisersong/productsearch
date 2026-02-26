"""分析节点：聚合产品列表并生成最终汇总报告。"""

from typing import Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from product_search.core.logger import logger
from product_search.state.graph_state import ProductSearchState
from product_search.tools.product_extractor import ProductInfo

SUMMARY_SYSTEM_PROMPT = """你是一个专业的企业产品分析师。
请根据提供的产品清单，生成一份结构清晰的企业产品线分析报告。

报告格式：
1. 总体概述（1-2句话）
2. 产品线分类（按类别分组，列出主要产品）
3. 产品特点总结

用中文回答，简洁专业。"""


def aggregate_results(state: ProductSearchState) -> dict:
    """聚合并去重产品列表（纯函数，无 LLM 调用）。"""
    products: List[ProductInfo] = state.get("products", [])

    # 按置信度降序排列
    sorted_products = sorted(products, key=lambda p: p.confidence, reverse=True)

    # 按类别统计
    by_category: Dict[str, List[ProductInfo]] = {}
    for p in sorted_products:
        by_category.setdefault(p.category, []).append(p)

    logger.info(f"[analyze_node] 聚合完成: {len(sorted_products)} 个产品，{len(by_category)} 个类别")

    return {
        "products": sorted_products,
        "messages": [AIMessage(content=f"聚合完成: {len(sorted_products)} 个产品，覆盖 {len(by_category)} 个类别")],
    }


async def format_output(state: ProductSearchState, llm: BaseChatModel) -> dict:
    """使用 LLM 生成最终汇总报告。"""
    company_name = state["company_name"]
    products: List[ProductInfo] = state.get("products", [])

    if not products:
        summary = f"未找到关于 {company_name} 的产品信息。请尝试换用不同的搜索引擎或检查企业名称是否正确。"
        return {"summary": summary}

    # 构建产品列表文本
    product_lines = []
    for p in products:
        line = f"- {p.name}（{p.category}）"
        if p.description:
            line += f"：{p.description}"
        product_lines.append(line)

    products_text = "\n".join(product_lines)

    logger.info(f"[analyze_node] 生成汇总报告: {len(products)} 个产品")

    try:
        response = await llm.ainvoke([
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=f"企业名称：{company_name}\n\n产品清单：\n{products_text}"),
        ])
        summary = response.content
    except Exception as e:
        logger.warning(f"生成汇总失败，使用简单格式: {e}")
        summary = f"{company_name} 产品列表（共 {len(products)} 个）：\n{products_text}"

    return {
        "summary": summary,
        "messages": [AIMessage(content="分析报告生成完毕")],
    }
