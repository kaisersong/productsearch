# ProductSearch

AI Agent，输入企业名称，自动搜索并整理该企业生产的所有产品信息。

基于 **LangGraph** 实现循环搜索工作流，支持多种 LLM（OpenAI / Anthropic / Ollama）和多种搜索引擎（DuckDuckGo / SerpAPI / Serper）。

---

## 安装

### 方式一：pipx 全局安装（推荐）

安装后可在任意目录使用，无需手动激活虚拟环境。

```bash
# 安装 pipx（如果尚未安装）
pip install pipx
python -m pipx ensurepath

# 安装 ProductSearch
pipx install git+https://github.com/kaisersong/productsearch.git

# 初始化配置文件
product-search init
```

配置文件会生成在：
- **macOS / Linux**：`~/.config/product-search/config.toml`
- **Windows**：`%APPDATA%\product-search\config.toml`

### 方式二：开发模式安装

```bash
git clone https://github.com/kaisersong/productsearch.git
cd productsearch
pip install -e ".[dev]"
```

配置文件放在项目内：

```bash
cp config/config.toml.example config/config.toml
# 编辑 config/config.toml，填入 API Key
```

---

## 配置

填入至少一个 LLM 的 API Key，推荐通过环境变量设置：

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# 或 Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

也可以直接写入配置文件 `config.toml`：

```toml
[llm]
provider = "openai"
model    = "gpt-4o-mini"
api_key  = "sk-..."

[llm.analysis]      # 用于最终汇总的模型，可单独配置更强的模型
model = "gpt-4o"

[search]
engine      = "duckduckgo"   # 免费，无需 Key
max_results = 10
```

---

## 使用

### 交互模式（REPL）

直接运行，进入类 Claude CLI 的交互会话：

```bash
product-search
```

```
╭─ ProductSearch interactive mode ──────────────────────╮
│  输入企业名称搜索产品，/help 查看所有命令，Ctrl+D 退出  │
╰────────────────────────────────────────────────────────╯

› 远景科技
⠋ 正在搜索 远景科技...  0:00:08
  找到 38 个产品

› /export excel 远景科技产品.xlsx
  ✓ 已导出 Excel：远景科技产品.xlsx

› /history
  #  企业    产品数
  1  远景科技    38

› /quit
```

**REPL 命令：**

| 命令 | 说明 |
|------|------|
| `<企业名称>` | 搜索该企业的产品信息 |
| `/batch <文件路径>` | 从 Excel 批量搜索，结果输出到同目录 |
| `/export [excel\|json\|text] [文件名]` | 导出上次搜索结果（默认 excel） |
| `/history` | 查看本次会话的搜索记录 |
| `/clear` | 清空屏幕 |
| `/help` | 显示帮助 |
| `/quit` 或 `Ctrl+D` | 退出 |
| `Ctrl+C` | 取消当前搜索 |
| `↑ / ↓` | 翻历史输入 |

**REPL 启动选项：**

```bash
product-search -n 1 --no-summary   # 每次搜索只迭代 1 轮，不生成 AI 汇总（更快）
product-search -v                   # 显示详细工作流日志
product-search --llm-config fast    # 使用 config.toml 中的 [llm.fast] 配置
```

---

### 单次搜索

```bash
# 基础搜索（表格输出）
product-search search "远景科技"

# JSON 格式
product-search search "远景科技" --output json

# 快速模式（1 轮迭代，不生成 AI 汇总）
product-search search "远景科技" -n 1 --no-summary

# 显示详细日志
product-search -v search "远景科技"
```

---

### 批量搜索（Excel 输入 → Excel 输出）

从 Excel 文件读取企业名称列表，逐一搜索，汇总输出到新 Excel。

```bash
# 基础用法（输出到输入文件同目录的 products_output.xlsx）
product-search batch 企业.xlsx

# 指定输出路径
product-search batch 企业.xlsx -o ~/Desktop/结果.xlsx

# 指定企业名称所在列（列名或列号）
product-search batch 企业.xlsx --company-column 企业名称
product-search batch 企业.xlsx --company-column 2

# 无表头文件
product-search batch 企业.xlsx --no-skip-header

# 快速模式
product-search batch 企业.xlsx -n 1 --no-summary
```

**输入 Excel 格式：** 每行一家企业，默认读取第一列，支持有/无表头。

**输出 Excel 包含两个工作表：**
- `产品列表`：每行一个产品，含企业名称 / 产品名称 / 类别 / 描述 / 置信度 / 来源 URL / AI 汇总
- `企业汇总`：每家企业的产品数量和 AI 分析报告

---

### Shell 自动补全

```bash
# bash
product-search completion bash >> ~/.bashrc

# zsh
product-search completion zsh >> ~/.zshrc

# fish
product-search completion fish > ~/.config/fish/completions/product-search.fish

# PowerShell (Windows)
product-search completion powershell >> $PROFILE
```

---

## 工作流

```
START → generate_queries → web_search → scrape_content → extract_products
                                                                ↓
                                                        should_continue?
                                                         /           \
                                                     YES(←返回)       NO
                                                                       ↓
                                                           aggregate_results
                                                                       ↓
                                                           format_output → END
```

最多迭代 3 次（可通过 `-n` 调整），每次生成新查询词扩大搜索范围。

---

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `llm.provider` | `openai` | LLM 提供商：`openai` / `anthropic` / `ollama` |
| `llm.model` | `gpt-4o-mini` | 模型名称 |
| `llm.api_key` | `""` | API Key（推荐用环境变量） |
| `llm.analysis.model` | 同 default | 汇总报告使用的模型，可单独指定更强模型 |
| `search.engine` | `duckduckgo` | 搜索引擎：`duckduckgo`（免费）/ `serpapi` / `serper` |
| `search.max_results` | `10` | 每次搜索返回最大结果数 |

---

## 测试

```bash
# 单元测试（无需 API Key）
pytest tests/unit/ -v -m unit

# 集成测试（需要真实 API Key）
OPENAI_API_KEY=sk-... pytest tests/integration/ -v -m integration
```

---

## 项目结构

```
src/product_search/
├── core/           # 配置、日志、异常
├── llm/            # LLM 工厂（多 Provider 支持）
├── tools/          # 搜索、爬虫、产品提取工具
├── state/          # LangGraph 状态定义
├── nodes/          # 工作流节点函数
├── graph/          # StateGraph 工作流定义
├── repl.py         # 交互式 REPL 模式
└── cli.py          # CLI 入口
```
