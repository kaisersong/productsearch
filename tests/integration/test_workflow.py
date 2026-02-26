"""集成测试：需要真实 API Key。

运行方式：
    OPENAI_API_KEY=sk-... pytest tests/integration/ -v -m integration
"""

import os

import pytest


# 如果没有 API Key，跳过整个集成测试模块
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"),
    reason="集成测试需要 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_huawei():
    """完整工作流测试：搜索华为产品（需要 API Key）。"""
    from product_search.graph.workflow import run_search

    state = await run_search(company_name="华为", max_iterations=1)

    products = state.get("products", [])
    assert len(products) > 0, "应找到至少 1 个华为产品"

    # 验证产品结构
    for p in products:
        assert p.name, "产品名称不能为空"
        assert p.category, "产品类别不能为空"
        assert 0.0 <= p.confidence <= 1.0, "置信度应在 0~1 范围内"

    # 验证摘要
    summary = state.get("summary", "")
    assert summary, "应生成产品汇总报告"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_apple():
    """完整工作流测试：搜索苹果公司产品（需要 API Key）。"""
    from product_search.graph.workflow import run_search

    state = await run_search(company_name="Apple Inc", max_iterations=1)

    products = state.get("products", [])
    assert len(products) > 0, "应找到至少 1 个 Apple 产品"

    # 应能找到 iPhone 或类似产品
    product_names = [p.name.lower() for p in products]
    known_products = ["iphone", "ipad", "mac", "apple watch", "airpods"]
    found = any(any(kp in name for kp in known_products) for name in product_names)
    assert found, f"应能找到 Apple 知名产品，实际找到: {product_names}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_with_no_results():
    """工作流对未知企业应优雅返回空结果（需要 API Key）。"""
    from product_search.graph.workflow import run_search

    # 随机不存在的企业名
    state = await run_search(company_name="XYZ不存在公司12345", max_iterations=1)

    # 不应抛出异常，应正常返回（可能是空列表）
    assert "products" in state
    assert "summary" in state


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_iteration_limit():
    """验证迭代次数限制有效（需要 API Key）。"""
    from product_search.graph.workflow import run_search

    state = await run_search(company_name="小米", max_iterations=2)

    # 迭代次数应 <= max_iterations
    assert state.get("iteration_count", 0) <= 2
