"""状态和条件边单元测试（无需 API Key）。"""

import pytest

from product_search.graph.conditions import should_continue
from product_search.nodes.analyze_node import aggregate_results
from product_search.tools.product_extractor import ProductInfo


class TestShouldContinue:
    @pytest.mark.unit
    def test_continue_when_should_and_below_max(self, base_state):
        state = {**base_state, "should_continue": True, "iteration_count": 1, "max_iterations": 3}
        assert should_continue(state) == "continue"

    @pytest.mark.unit
    def test_aggregate_when_max_reached(self, base_state):
        state = {**base_state, "should_continue": True, "iteration_count": 3, "max_iterations": 3}
        assert should_continue(state) == "aggregate"

    @pytest.mark.unit
    def test_aggregate_when_no_continue_flag(self, base_state):
        state = {**base_state, "should_continue": False, "iteration_count": 1, "max_iterations": 3}
        assert should_continue(state) == "aggregate"

    @pytest.mark.unit
    def test_aggregate_when_zero_iterations_and_no_continue(self, base_state):
        state = {**base_state, "should_continue": False, "iteration_count": 0}
        assert should_continue(state) == "aggregate"


class TestAggregateResults:
    @pytest.mark.unit
    def test_sorts_by_confidence(self, base_state, sample_products):
        state = {**base_state, "products": sample_products}
        result = aggregate_results(state)
        products = result["products"]
        confidences = [p.confidence for p in products]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.unit
    def test_empty_products(self, base_state):
        state = {**base_state, "products": []}
        result = aggregate_results(state)
        assert result["products"] == []

    @pytest.mark.unit
    def test_returns_messages(self, base_state, sample_products):
        state = {**base_state, "products": sample_products}
        result = aggregate_results(state)
        assert "messages" in result
        assert len(result["messages"]) > 0


class TestInitialState:
    @pytest.mark.unit
    def test_base_state_has_required_keys(self, base_state):
        required_keys = [
            "company_name", "messages", "search_queries", "all_queries_used",
            "raw_search_results", "scraped_content", "scraped_urls",
            "iteration_count", "max_iterations", "should_continue",
            "products", "summary",
        ]
        for key in required_keys:
            assert key in base_state, f"缺少必要的状态键: {key}"

    @pytest.mark.unit
    def test_initial_iteration_count_is_zero(self, base_state):
        assert base_state["iteration_count"] == 0

    @pytest.mark.unit
    def test_initial_products_empty(self, base_state):
        assert base_state["products"] == []
