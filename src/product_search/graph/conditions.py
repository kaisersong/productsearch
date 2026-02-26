"""LangGraph 条件边判断函数。"""

from product_search.core.logger import logger
from product_search.state.graph_state import ProductSearchState


def should_continue(state: ProductSearchState) -> str:
    """判断是否继续搜索迭代。

    Returns:
        "continue": 继续下一轮搜索
        "aggregate": 结束搜索，进入聚合分析
    """
    should = state.get("should_continue", False)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)

    logger.debug(
        f"[conditions] should_continue={should}, "
        f"iteration={iteration}/{max_iter}, "
        f"products={len(state.get('products', []))}"
    )

    if should and iteration < max_iter:
        return "continue"
    return "aggregate"
