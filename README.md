# Gold Data Reading for AI Agents · 黄金读数 Agent 分发包

[![Wangxian111/xaudaily-gold-data MCP server](https://glama.ai/mcp/servers/Wangxian111/xaudaily-gold-data/badges/score.svg)](https://glama.ai/mcp/servers/Wangxian111/xaudaily-gold-data)

## English

An [Agent Skill](SKILL.md) plus a **zero-dependency MCP server** that give AI agents daily gold and macro
readings from [xaudaily.com](https://xaudaily.com/) — numbers an agent can actually cite.

**Why not just let the agent search the web?** Every field carries its own `source` and `asOf`/`date`, so a
citation can be checked rather than trusted. When an upstream source fails, the site keeps the last good value
and flags the field `stale: true` instead of silently serving an old number. And the figures are the same ones
the site renders — same snapshot, same code path — so the JSON and the page can never disagree.

**Two tools, over stdio:**

| Tool | Returns |
|---|---|
| `get_gold_readings` | Full JSON readings (schema `xaudaily.readings/v1`), optionally trimmed with `fields=[...]` |
| `get_gold_daily_brief` | Today's headline numbers as Markdown (a few KB) |

**What's inside:** COMEX gold and Shanghai Au99.99 (with a ~30-minute live tick), US CPI / core PCE / nonfarm
payrolls / PPI, DXY, Treasury 10Y and 30Y yields, VIX, SPDR gold ETF holdings, the fed funds rate and
Polymarket odds for the next FOMC decision, IMF central-bank gold buying, Brent/WTI crude, US debt, plus a
rule-based gold driver score and event estimates — one request, about 60 KB, instead of stitching together a
dozen sources.

**Updated twice a day** (06:30 and 22:40 JST) with a ~30-minute gold tick. These are *daily readings, not a
real-time feed* — please don't describe them as real-time or guaranteed accurate. The data is not investment
advice.

**Files:** `SKILL.md` (the skill), `mcp_server.py` (the server — standard library only), `Dockerfile` (for
container-based catalogs), `glama.json`, `examples/` (copy-paste curl and Python), `WIDGET.md` (an embeddable
gold badge).

### Install

**As an MCP server.** One Python file, nothing to `pip install`:

```json
{
  "mcpServers": {
    "xaudaily": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "XAUDaily_READINGS_URL": "https://xaudaily.com/readings.en.json?src=skill-mcp",
        "XAUDaily_BRIEF_URL": "https://xaudaily.com/brief.en.md?src=skill-mcp"
      }
    }
  }
}
```

**With Docker** (the same image MCP catalogs build for introspection):

```bash
docker build -t xaudaily-mcp .
docker run -i --rm xaudaily-mcp        # then speak JSON-RPC on stdin
```

**As an Agent Skill:** copy this directory (or just `SKILL.md`) into your runtime's skills directory.

### Endpoints

- English payload: `https://xaudaily.com/readings.en.json?src=skill-github`
- Chinese payload: `https://xaudaily.com/readings.json?src=skill-github` — **same snapshot, same numbers**, same
  field paths; only the string values (units, sources, caveats) are Chinese
- Briefs: `/brief.en.md` and `/brief.md`

### License and attribution

Data is **CC BY 4.0**. **Attribution with a link is required** — e.g.
*Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)*. Please don't repackage the dataset as your
own. For commercial use or redistribution, contact xaudaily@163.com.

*中文说明见下方 ↓*

---

## 中文说明

给 AI Agent 用的**黄金宏观数据**接入包：一份 Agent Skill 说明书 + 一个零依赖的 MCP server。

- 数据源：[xaudaily.com](https://xaudaily.com/)（品牌「黄金读数 / Gold Data Reading · XAU Daily」），纯静态黄金宏观数据仪表盘
- 端点（英文）：`https://xaudaily.com/readings.en.json?src=skill-github`（JSON，schema `xaudaily.readings/v1`）
- 端点（中文）：`https://xaudaily.com/readings.json?src=skill-github` —— **同一份快照、同一批数字**，
  字段路径完全一致，只是字符串值（单位/来源/口径说明）为中文；英文简报 `/brief.en.md`，中文简报 `/brief.md`
- 许可：**CC-BY-4.0**（署名 + 附链接）

```
skill-repo/
├── SKILL.md            # Agent Skill：字段说明、信封约定、常见坑（中文为主，关键段落英文）
├── mcp_server.py       # MCP server：纯 Python 标准库，stdio 传输，两个工具
├── Dockerfile          # 极简镜像，给 Glama 这类按容器做 introspection 的目录用
├── glama.json          # 声明维护者（Glama 的收录元数据）
├── README.md           # 本文件（英文在前，中文见本节）
├── LICENSE             # CC-BY-4.0 完整法律文本
├── WIDGET.md           # 可嵌入金价徽标的嵌入说明（给你的网站/README 用）
└── examples/
    ├── curl.md         # 可直接复制运行的 curl 示例
    └── python.md       # 只用标准库的 Python 示例
```

---

## 这是什么

xaudaily.com 每天 06:30 与 22:40（JST）自动抓取、校验并渲染一批黄金宏观读数，同时把它输出成一份**给机器读的 JSON**。这个仓库把那份额外的机器可读产出包装成 Agent 能直接消费的形态：

- **`SKILL.md`** —— 一份 Agent Skills 约定的说明书：端点表、完整字段结构（异构结构逐个列出）、取数示例、数据口径、更新节奏、署名要求、踩过的坑。
- **`mcp_server.py`** —— 支持 MCP 的客户端（Claude Desktop 等）挂上就能用的 server，两个工具：`get_gold_readings`（全量 JSON，可按字段裁剪）与 `get_gold_daily_brief`（当日 Markdown 简报）。**只用 Python 标准库**，不装任何第三方包。

## 为什么值得用它（而不是让 Agent 现抓现猜）

1. **每个字段自带出处与截止日。** 每个字段里有 `source`（数据来源）和 `asOf`/`date`（数据截止日），`meta` 里还有口径说明、免责声明与署名要求。Agent 引用时能给出可核查的出处，而不是一个来路不明的数字。
2. **降级是显式的。** 某个上游源抓取失败时，站点沿用上一次成功值并把该字段标成 `stale: true` —— 消费方能看出「这不是最新一期」，而不是被悄悄喂了旧数字。
3. **字段稳定、结构有版本。** 顶层 `schema` 恒为 `xaudaily.readings/v1`，改结构时会换值；`extra` 区可以加新字段而不动顶层键，所以你的代码不容易因为上游加字段而挂掉。
4. **单次抓取就够。** 金价、沪金、CPI、PCE、非农、PPI、DXY、美债 10Y/30Y、VIX、SPDR 持仓、联邦基金利率、FOMC 决议概率、央行购金、原油、美国债务、驱动因子评分与事件预判，全在一次请求里（约 60 KB），不用拼十几个来源。
5. **零依赖 = 不会腐烂。** `mcp_server.py` 是单个 `stdlib`-only 的 Python 文件，没有 `requirements`，几年后照样能跑。

## 安装

### 方式一：作为 Agent Skill

把本目录（或其中的 `SKILL.md`）放进你的 Agent 运行时的 skills 目录即可 —— Agent Skills 约定是「一个目录一份技能，入口是 `SKILL.md`」：

```bash
git clone <本仓库地址> gold-market-readings
cp -r gold-market-readings ~/.your-agent/skills/gold-market-readings/
# 或者直接把 SKILL.md 放到你现有的 skills 目录下
```

Agent 会读它的 frontmatter（`name` / `description`）判断何时该用：涉及金价、通胀（CPI/PCE）、非农、FOMC 决议概率、央行购金、美债收益率、DXY、黄金驱动因子时触发。

### 方式二：作为 MCP server

`mcp_server.py` 走 stdio 传输，不需要端口、不需要守护进程。把它加进客户端的 MCP 配置：

```json
{
  "mcpServers": {
    "xaudaily": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "XAUDaily_READINGS_URL": "https://xaudaily.com/readings.en.json?src=skill-mcp",
        "XAUDaily_BRIEF_URL": "https://xaudaily.com/brief.en.md?src=skill-mcp"
      }
    }
  }
}
```

Windows 上把 `command` 写成解释器的完整路径最稳妥。手动试一下：

```bash
python3 mcp_server.py            # 它会等待 stdin 上的 JSON-RPC 报文
```

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `XAUDaily_READINGS_URL` | `https://xaudaily.com/readings.en.json?src=skill-mcp` | 覆盖读数端点（默认值＝英文端点，已带渠道参数） |
| `XAUDaily_BRIEF_URL` | `https://xaudaily.com/brief.en.md?src=skill-mcp` | 覆盖简报端点（默认值＝英文端点） |
| `XAUDaily_READINGS_FILE` | 空 | 指向本地一份 `readings.json` 副本，用于**离线自测**（设了就优先读文件，不出网） |
| `XAUDaily_TIMEOUT` | `20` | 单次 HTTP 超时秒数 |

工具的行为约定（也是 `SKILL.md` 里写给 Agent 的部分）：

- 未知方法返回 JSON-RPC error（`-32601`），不会崩；`notifications/*` 一律不响应。
- 网络超时、HTTP 非 200、JSON 解析失败，都转成**结构化的 tool error 结果**（`isError: true` + `kind`/`detail`/`hint`），进程照常活着 —— 一次网络抖动不该让 Agent 的整个会话失去这个工具。
- stdout 上只有 JSON-RPC 报文；日志一律走 stderr。

### 方式三：作为 Docker 容器

仓库根目录的 `Dockerfile` 就是给容器化场景用的（Glama 这类目录按它构建镜像、启动进程、读 `tools/list` 做 introspection）：

```bash
docker build -t xaudaily-mcp .
docker run -i --rm xaudaily-mcp        # 然后往 stdin 写 JSON-RPC
```

## 示例

```bash
# 全量读数
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' -o readings.json

# 只要今天的关键数字（Markdown，几 KB）
curl -sS 'https://xaudaily.com/brief.md?src=skill-github'
```

```python
import json, urllib.request

with urllib.request.urlopen("https://xaudaily.com/readings.json?src=skill-github", timeout=20) as r:
    d = json.load(r)
print(d["generated_at"], "| 数据截止", d["data_asof"])
print("沪金", d["readings"]["au"]["last"], d["readings"]["au"]["unit"])
```

MCP 侧一次 `tools/call`（收到的是两个 content 块：署名提醒 + 数据本体）：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_gold_readings","arguments":{"fields":["gold","extra.polymarket"]}}}
```

更多可直接复制运行的例子见 `examples/curl.md` 与 `examples/python.md`。

## 请保留 URL 里的 `?src=`

所有示例与文档里的 URL 都带 `?src=<渠道>`，例如 `?src=skill-github`、`?src=skill-mcp`。这不是跟踪参数，而是这个数据源**能被持续维护的前提**：

- 带 `?src=` 的读数请求返回 `Cache-Control: no-store`，绕开 CDN 边缘缓存，**每一次抓取都会真实落到源站访问日志**；
- 不带参数时，响应走 `Cache-Control: public, max-age=300`，多次抓取会被边缘缓存合并成一次 —— 站长看到的就只有「3 次访问」，而实际可能是「1000 次消费」。

去掉参数请求**不会失败**，但渠道归因就此消失，也就没人说得清这份数据究竟有没有被用。所以：**请不要删掉它**；想区分你自己的渠道，把值改成你的名字（如 `?src=my-agent-prod`）完全可以，只用 `[a-z0-9-]` 这类字符即可。

## 更新节奏（请如实转述）

- 每天 **两次**全量更新：06:30 / 22:40（JST，东京时间；北京时间 05:30 / 21:40）。所有字段、存档页、`brief.md` 在这一刻刷新。
- 金价与沪金**另外**每约 30 分钟刷新一次实时 tick（只影响金价类字段）。
- 其余宏观指标是月频/季频数据（CPI、非农、GDP 等），本来就不每天变。
- **这不是行情终端。** 请不要把它描述为「实时行情」或「保证准确」：数据由程序从公开来源抓取，可能滞后、被修订或缺失（缺失时看 `stale` 字段）。准确说法是「每日两次更新的宏观读数 + 约 30 分钟一次的金价 tick」。

## 许可与引用

- 许可：**CC-BY-4.0**（Creative Commons Attribution 4.0 International，SPDX：`CC-BY-4.0`，全文 <https://creativecommons.org/licenses/by/4.0/>）。
- **必须署名并附链接。** 推荐写法：*数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)*（英文：*Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)*）。
- 不得把本站数据整体或实质部分再包装成「自有数据源」「自研 API」「独家数据」发布或转售。
- 商用、批量再分发、镜像、长期落库或作为训练语料：请先联系 **xaudaily@163.com**。
- 免责声明：数据由程序从公开来源抓取与呈现，不构成投资建议，不提供买卖指导；概率类字段是市场定价或规则模型估计，不是预测保证。

## 可嵌入挂件（免费，给你的站点或 README 用）

如果这份数据对你的读者有用，可以顺手嵌一枚**每日自动更新的金价徽标**：

```html
<a href="https://xaudaily.com/?utm_source=widget&amp;utm_medium=embed&amp;utm_campaign=gold-badge">
  <img src="https://xaudaily.com/widget/gold-badge.svg" width="320" height="96"
       alt="今日金价 · 黄金读数 xaudaily.com">
</a>
```

- 图由本站托管，每约 30 分钟跟着金价 tick 重生成，**你不需要自己更新**；
- 可点击的链接必须由**外层 `<a>` 包裹 `<img>`** 实现（`<img>` 加载的 SVG，其内部链接点不动）；请**不要**把图下载自托管——那样会永远停在旧价，也丢失归因；
- 深色站点用 `/widget/gold-badge-dark.svg`；配色是**中国习惯（红涨绿跌）**，面向英文读者请在嵌入处补一句 "red = up"；
- 完整说明与三种嵌入写法见 **[WIDGET.md](WIDGET.md)**；在线预览：<https://xaudaily.com/widget/>

## 联系

问题、字段需求、渠道归因（想让你自己的 agent 渠道单独出现在统计里）、商用授权：**xaudaily@163.com**

站点：<https://xaudaily.com/> · Agent 自述文件：<https://xaudaily.com/llms.txt?src=skill-github> · 历史存档：<https://xaudaily.com/d/?src=skill-github>
