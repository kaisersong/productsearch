---
name: product-search
version: "0.2.0"
description: 通过 AI Agent 搜索企业产品信息。当用户提到"搜索产品"、"查找企业产品"、"产品信息"、"批量搜索企业"、"/product-search"时使用此 skill。支持单企业搜索（search）和批量 Excel 导入（batch），支持管理 LLM 模型配置（llm add/list/use/remove）。
allowed-tools: Bash, Read, Write
---

# ProductSearch Skill

## 用途

搜索企业产品信息的 AI Agent 工具，支持三类操作：
- **search**：搜索单家企业的产品信息
- **batch**：从 Excel 批量读取企业，逐一搜索，输出汇总 Excel
- **llm**：管理 LLM 模型配置（添加、切换、查看、删除）

## 命令路由规则

解析 `$ARGUMENTS`，按以下规则决定执行哪条命令：

| 用户输入形如 | 实际执行 |
|---|---|
| `batch <文件> [选项]` | `product-search batch <文件> [选项]` |
| `llm add <name> [选项]` | `product-search llm add <name> [选项]` |
| `llm use <name>` | `product-search llm use <name>` |
| `llm list` | `product-search llm list` |
| `llm remove <name>` | `product-search llm remove <name>` |
| `--help` 或 `help` | `product-search --help` |
| `<企业名称> [选项]` | `product-search search "<企业名称>" [选项]` |

> 第一个词是 `batch` → batch 命令；`llm` → llm 命令；否则视为企业名称 → search 命令。

## 执行步骤

1. **解析参数**：检查 `$ARGUMENTS` 第一个词
2. **环境检查**：确认 `product-search` 命令可用（见下方）
3. **执行命令**：根据路由规则运行对应子命令
4. **展示结果**：将输出呈现给用户

## search 命令

搜索单家企业的产品信息。

```bash
product-search search "<企业名称>" [选项]
```

**选项：**
- `--output [table|json|text]`：输出格式，默认 table
- `--max-iterations N`：最大搜索迭代次数，默认 3（设为 1-2 更快）
- `--no-summary`：跳过 AI 汇总报告
- `--llm-config <name>`：使用指定 LLM 配置

**示例：**

用户说：`/product-search 示例科技`
```bash
product-search search "示例科技"
```

用户说：`/product-search Acme Corp --output json --max-iterations 1`
```bash
product-search search "Acme Corp" --output json --max-iterations 1
```

## batch 命令

从 Excel 批量读取企业名称，搜索每家企业的产品，输出到新 Excel 文件。

```bash
product-search batch <输入Excel> [选项]
```

**选项：**
- `--output / -o <路径>`：输出 Excel 路径，默认在输入文件同目录生成 `products_output.xlsx`
- `--company-column / -c <列名或列号>`：企业名称所在列，默认第 1 列
- `--sheet <名称>`：读取的工作表，默认第一个
- `--skip-header / --no-skip-header`：是否跳过表头行，默认跳过
- `--max-iterations N`：每家企业最大搜索迭代次数，默认 3
- `--no-summary`：跳过 AI 汇总报告
- `--llm-config <name>`：LLM 配置名称

**输出 Excel 包含两个工作表：**
- `产品列表`：每行一个产品，列为企业名称/产品名称/类别/描述/置信度/来源URL/AI汇总
- `企业汇总`：每行一家企业，列为企业名称/产品数量/产品类别数/AI汇总

**示例：**

用户说：`/product-search batch 企业.xlsx`
```bash
product-search batch 企业.xlsx
```

用户说：`/product-search batch ~/Downloads/list.xlsx --output ~/Desktop/result.xlsx`
```bash
product-search batch ~/Downloads/list.xlsx --output ~/Desktop/result.xlsx
```

## llm 命令

管理 LLM 模型配置，无需手动编辑配置文件。

```bash
# 添加配置（名称与 provider 同名时自动推断）
product-search llm add deepseek --api-key sk-xxx
product-search llm add kimi --model moonshot-v1-32k --api-key sk-xxx

# 设为默认（同时更新 default 和 analysis）
product-search llm use deepseek

# 查看所有配置
product-search llm list

# 删除配置
product-search llm remove kimi
```

**支持的 provider：**
`openai` / `anthropic` / `ollama` / `deepseek` / `glm` / `minimax` / `kimi` / `qwen` / `seed`

## 环境检查

如果 `product-search` 命令不存在，提示用户：
```
ProductSearch 未安装，请先执行：
pipx install git+https://github.com/kaisersong/productsearch.git
```

## 前提条件

- 已安装：`pipx install git+https://github.com/kaisersong/productsearch.git`
- 已配置 LLM API Key，推荐通过命令行配置：
  ```bash
  product-search llm add deepseek --api-key sk-xxx
  product-search llm use deepseek
  ```
- 或通过环境变量：`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` 等

## 文件路径处理

当用户提供的 Excel 文件名不含路径时（如 `企业.xlsx`），先在以下位置按顺序查找：
1. 当前工作目录
2. `~/Downloads/`

找到后使用绝对路径执行命令，避免找不到文件的错误。
