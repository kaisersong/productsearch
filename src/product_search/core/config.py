"""单例配置管理，支持 TOML 文件 + 环境变量。"""

import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

from product_search.core.exceptions import ConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_project_root() -> Path:
    """获取项目根目录（src/product_search/core/ 上三级）。"""
    return Path(__file__).resolve().parent.parent.parent.parent


def get_user_config_dir() -> Path:
    """获取跨平台用户配置目录。

    - Windows:  %APPDATA%\\product-search
    - macOS/Linux: ~/.config/product-search
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "product-search"


# 内置的最简配置模板（用于 init 命令）
DEFAULT_CONFIG_TEMPLATE = """\
# ProductSearch 配置文件
# 文档: https://github.com/kaisersong/productsearch
#
# 支持的 provider:
#   openai | anthropic | ollama | deepseek | glm | minimax | kimi | qwen | seed
# 推荐通过环境变量设置 API Key，无需写入此文件：
#   OPENAI_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY /
#   MOONSHOT_API_KEY / DASHSCOPE_API_KEY / ZHIPU_API_KEY / ARK_API_KEY

[llm.default]
provider = "openai"
model = "gpt-4o-mini"
api_key = ""                 # 留空则从环境变量 OPENAI_API_KEY 读取

# 用于最终汇总分析的模型（可单独配置更强的模型，可选）
[llm.analysis]
provider = "openai"
model = "gpt-4o-mini"
api_key = ""

[search]
# 搜索引擎: duckduckgo（免费）| serpapi | serper
engine = "duckduckgo"
max_results = 10
timeout = 30
"""


PROJECT_ROOT = get_project_root()


# 各 provider 对应的环境变量名
_PROVIDER_ENV_KEYS: Dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "glm":       "ZHIPU_API_KEY",
    "minimax":   "MINIMAX_API_KEY",
    "kimi":      "MOONSHOT_API_KEY",
    "qwen":      "DASHSCOPE_API_KEY",
    "seed":      "ARK_API_KEY",
}


class LLMSettings(BaseModel):
    provider: str = Field(
        default="openai",
        description="LLM 提供商: openai | anthropic | ollama | deepseek | glm | minimax | kimi | qwen | seed",
    )
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    api_key: str = Field(default="", description="API Key（可留空从环境变量读取）")
    base_url: str = Field(default="", description="API Base URL（留空使用官方地址）")
    max_tokens: int = Field(default=4096, description="最大 token 数")
    temperature: float = Field(default=0.7, description="采样温度")

    def effective_api_key(self) -> str:
        """返回有效的 API Key（配置文件 > 环境变量）。"""
        if self.api_key:
            return self.api_key
        provider = self.provider.lower()
        if provider == "anthropic":
            # 兼容标准变量名和旧变量名
            return (
                os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or ""
            )
        env_key = _PROVIDER_ENV_KEYS.get(provider, "")
        return os.environ.get(env_key, "") if env_key else ""

    def effective_base_url(self) -> Optional[str]:
        """返回有效的 Base URL（配置文件 > 环境变量）。

        国产模型的默认 base_url 由 factory.py 的 _OPENAI_COMPATIBLE_PROVIDERS 提供，
        此处仅处理用户自定义覆盖的情形。
        """
        if self.base_url:
            return self.base_url
        provider = self.provider.lower()
        if provider == "anthropic":
            return os.environ.get("ANTHROPIC_BASE_URL") or None
        if provider == "openai":
            return os.environ.get("OPENAI_BASE_URL") or None
        return None


class SearchSettings(BaseModel):
    engine: str = Field(default="duckduckgo", description="搜索引擎: duckduckgo | serpapi | serper")
    api_key: str = Field(default="", description="搜索引擎 API Key")
    max_results: int = Field(default=10, description="每次搜索最大结果数")
    timeout: int = Field(default=30, description="搜索超时秒数")

    def effective_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_map = {
            "serpapi": "SERPAPI_API_KEY",
            "serper": "SERPER_API_KEY",
        }
        env_key = env_map.get(self.engine, "")
        return os.environ.get(env_key, "")


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings] = Field(default_factory=dict)
    search: SearchSettings = Field(default_factory=SearchSettings)


class Config:
    """线程安全的单例配置类。"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config: Optional[AppConfig] = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_writable_path() -> Path:
        """返回可写的配置文件路径（本地开发 > 用户目录，不允许写入 example）。"""
        local = PROJECT_ROOT / "config" / "config.toml"
        if local.exists():
            return local
        user_cfg = get_user_config_dir() / "config.toml"
        if user_cfg.exists():
            return user_cfg
        raise ConfigError(
            "未找到可写的配置文件。请先运行 [bold]product-search init[/bold] 创建配置文件。"
        )

    @staticmethod
    def _get_config_path() -> Path:
        """按优先级查找配置文件：

        1. 项目本地 config/config.toml（开发模式）
        2. 用户配置目录（pipx / 全局安装）
        3. 项目内示例配置（兜底）
        """
        # 1. 项目本地（开发模式优先）
        local = PROJECT_ROOT / "config" / "config.toml"
        if local.exists():
            return local

        # 2. 用户配置目录
        user_cfg = get_user_config_dir() / "config.toml"
        if user_cfg.exists():
            return user_cfg

        # 3. 示例配置兜底
        example = PROJECT_ROOT / "config" / "config.toml.example"
        if example.exists():
            return example

        raise ConfigError(
            "未找到配置文件。请运行 [bold]product-search init[/bold] 初始化配置，"
            "或手动创建配置文件。"
        )

    def _load_raw(self) -> dict:
        config_path = self._get_config_path()
        with config_path.open("rb") as f:
            return tomllib.load(f)

    def _load_initial_config(self):
        try:
            raw = self._load_raw()
        except ConfigError:
            raw = {}

        # 解析 LLM 配置
        raw_llm = raw.get("llm", {})
        llm_configs: Dict[str, LLMSettings] = {}

        # 收集顶层 LLM 字段作为 default
        default_fields = {k: v for k, v in raw_llm.items() if not isinstance(v, dict)}
        if default_fields:
            llm_configs["default"] = LLMSettings(**default_fields)
        else:
            llm_configs["default"] = LLMSettings()

        # 收集子表（如 [llm.analysis]）
        for name, sub in raw_llm.items():
            if isinstance(sub, dict):
                merged = {**llm_configs["default"].model_dump(), **sub}
                llm_configs[name] = LLMSettings(**merged)

        # 解析搜索配置
        raw_search = raw.get("search", {})
        search_config = SearchSettings(**raw_search) if raw_search else SearchSettings()

        self._config = AppConfig(llm=llm_configs, search=search_config)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    def get_llm(self, name: str = "default") -> LLMSettings:
        """获取指定名称的 LLM 配置，不存在则退回 default。"""
        return self._config.llm.get(name, self._config.llm["default"])

    @property
    def search(self) -> SearchSettings:
        return self._config.search

    def writable_config_path(self) -> Path:
        """返回可写的配置文件路径，用于 llm add/remove 等写操作。"""
        return self._get_writable_path()


config = Config()
