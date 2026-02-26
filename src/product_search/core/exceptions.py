"""自定义异常类。"""


class ProductSearchError(Exception):
    """ProductSearch 基础异常。"""


class ConfigError(ProductSearchError):
    """配置错误。"""


class LLMError(ProductSearchError):
    """LLM 调用错误。"""


class SearchError(ProductSearchError):
    """搜索工具错误。"""


class ScraperError(ProductSearchError):
    """网页抓取错误。"""


class ExtractionError(ProductSearchError):
    """产品提取错误。"""
