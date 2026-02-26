"""LLM 工厂，通过配置灵活切换 OpenAI / Anthropic / Ollama 及国产大模型。"""

from langchain_core.language_models import BaseChatModel

from product_search.core.config import LLMSettings, config
from product_search.core.exceptions import LLMError
from product_search.core.logger import logger

# OpenAI 兼容协议的国产大模型，key 为 provider 名称，value 为默认 base_url
_OPENAI_COMPATIBLE_PROVIDERS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "glm":      "https://open.bigmodel.cn/api/paas/v4",
    "minimax":  "https://api.minimax.chat/v1",
    "kimi":     "https://api.moonshot.cn/v1",
    "qwen":     "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "seed":     "https://ark.volces.com/api/v3",
}

_ALL_PROVIDERS = "openai, anthropic, ollama, " + ", ".join(_OPENAI_COMPATIBLE_PROVIDERS)


def create_llm(config_name: str = "default") -> BaseChatModel:
    """根据配置名称创建对应的 LangChain Chat 模型。

    Args:
        config_name: 配置块名称，对应 config.toml 中的 [llm.<name>] 节。

    Returns:
        LangChain BaseChatModel 实例。

    Raises:
        LLMError: 不支持的 Provider 或缺少 API Key。
    """
    settings: LLMSettings = config.get_llm(config_name)
    provider = settings.provider.lower()
    api_key = settings.effective_api_key()
    base_url = settings.effective_base_url()

    logger.debug(f"创建 LLM: provider={provider}, model={settings.model}, config={config_name}")

    if provider == "openai":
        return _create_openai(settings, api_key, base_url)
    elif provider == "anthropic":
        return _create_anthropic(settings, api_key)
    elif provider == "ollama":
        return _create_ollama(settings)
    elif provider in _OPENAI_COMPATIBLE_PROVIDERS:
        # 未在配置文件中指定 base_url 时，使用该 provider 的默认地址
        if not base_url:
            base_url = _OPENAI_COMPATIBLE_PROVIDERS[provider]
        return _create_openai(settings, api_key, base_url)
    else:
        raise LLMError(f"不支持的 LLM Provider: {provider}。支持: {_ALL_PROVIDERS}")


def _create_openai(settings: LLMSettings, api_key: str, base_url: str | None) -> BaseChatModel:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise LLMError("请安装 langchain-openai: pip install langchain-openai")

    if not api_key:
        env_hint = {
            "deepseek": "DEEPSEEK_API_KEY",
            "glm":      "ZHIPU_API_KEY",
            "minimax":  "MINIMAX_API_KEY",
            "kimi":     "MOONSHOT_API_KEY",
            "qwen":     "DASHSCOPE_API_KEY",
            "seed":     "ARK_API_KEY",
        }.get(settings.provider.lower(), "OPENAI_API_KEY")
        raise LLMError(
            f"API Key 未配置（provider={settings.provider}）。"
            f"请设置 {env_hint} 环境变量或在 config.toml 中配置 api_key。"
        )

    kwargs = {
        "model": settings.model,
        "api_key": api_key,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)


def _create_anthropic(settings: LLMSettings, api_key: str) -> BaseChatModel:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise LLMError("请安装 langchain-anthropic: pip install langchain-anthropic")

    if not api_key:
        raise LLMError("Anthropic API Key 未配置。请设置 ANTHROPIC_API_KEY 环境变量或在 config.toml 中配置。")

    base_url = settings.effective_base_url()
    kwargs = {
        "model": settings.model,
        "api_key": api_key,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatAnthropic(**kwargs)


def _create_ollama(settings: LLMSettings) -> BaseChatModel:
    try:
        from langchain_community.chat_models import ChatOllama
    except ImportError:
        raise LLMError("请安装 langchain-community: pip install langchain-community")

    base_url = settings.base_url or "http://localhost:11434"
    return ChatOllama(
        model=settings.model,
        base_url=base_url,
        num_predict=settings.max_tokens,
        temperature=settings.temperature,
    )
