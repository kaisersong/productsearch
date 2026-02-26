"""使用 LLM 从文本中结构化提取产品信息。"""

import json
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from product_search.core.exceptions import ExtractionError
from product_search.core.logger import logger

SYSTEM_PROMPT = """你是一个专业的产品信息提取助手。
你的任务是从给定的网页文本中，提取指定企业的产品信息。

请严格按照以下 JSON 格式返回，不要添加任何额外说明：
{
  "products": [
    {
      "name": "产品名称",
      "category": "产品类别（如：手机、笔记本电脑、家电等）",
      "description": "简短描述（50字以内）",
      "source_url": "信息来源URL（如果有）",
      "confidence": 0.9
    }
  ]
}

注意：
1. 只提取真实存在的产品，不要猜测
2. confidence 为 0.0~1.0 的置信度，基于信息的明确程度
3. 如果文本中没有相关产品信息，返回 {"products": []}
4. 同一产品不要重复提取
"""

EXTRACT_TEMPLATE = """企业名称：{company_name}
来源URL：{source_url}

网页内容：
{content}

请提取上述内容中关于"{company_name}"的产品信息。"""


class ProductInfo(BaseModel):
    """单个产品信息。"""

    name: str = Field(description="产品名称")
    category: str = Field(description="产品类别")
    description: str = Field(default="", description="产品简短描述")
    source_url: str = Field(default="", description="信息来源 URL")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度 0~1")


class ProductExtractor:
    """LLM 驱动的产品信息提取器。"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def extract(
        self,
        content: str,
        company_name: str,
        source_url: str = "",
    ) -> List[ProductInfo]:
        """从文本中提取产品信息。

        Args:
            content: 网页正文文本。
            company_name: 目标企业名称。
            source_url: 内容来源 URL，用于标注。

        Returns:
            ProductInfo 列表。

        Raises:
            ExtractionError: LLM 调用或解析失败时抛出。
        """
        if not content.strip():
            return []

        user_prompt = EXTRACT_TEMPLATE.format(
            company_name=company_name,
            source_url=source_url or "未知",
            content=content[:6000],  # 限制输入长度
        )

        logger.debug(f"提取产品信息: company={company_name}, url={source_url}")

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            raw_text = response.content

            products = self._parse_response(raw_text, source_url)
            logger.debug(f"提取到 {len(products)} 个产品: {[p.name for p in products]}")
            return products

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"LLM 提取失败: {e}") from e

    def _parse_response(self, raw_text: str, source_url: str) -> List[ProductInfo]:
        """解析 LLM 返回的 JSON 文本。"""
        # 尝试提取 JSON 块
        text = raw_text.strip()
        if "```" in text:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
            if match:
                text = match.group(1)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败，尝试提取片段: {e}")
            # 尝试找到 JSON 对象
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    return []
            else:
                return []

        products = []
        for item in data.get("products", []):
            try:
                if not item.get("source_url"):
                    item["source_url"] = source_url
                products.append(ProductInfo(**item))
            except Exception as e:
                logger.warning(f"跳过无效产品条目: {item}, 错误: {e}")

        return products
