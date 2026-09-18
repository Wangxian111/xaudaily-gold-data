#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄金读数 MCP server（xaudaily.com）—— 纯 Python 标准库实现，stdio 传输。

【这是什么】
    把 https://xaudaily.com/readings.json?src=skill-mcp（黄金宏观每日读数，schema
    xaudaily.readings/v1）与 https://xaudaily.com/brief.md?src=skill-mcp（当日纯文本简报）
    包装成 MCP（Model Context Protocol）工具的极简 server。只用 Python 3 标准库：本站的数据
    管道本来就是「纯 stdlib、零依赖」的设计，MCP server 也照这个来 —— 不用 pip install mcp、
    不用虚拟环境，一个 .py 复制过去就能跑，长期放着也不会因为依赖腐烂而失效。

【怎么跑】
    python3 mcp_server.py
    传输方式是 stdio：从 stdin 逐行读 JSON-RPC 2.0 报文（一行一条，newline-delimited），
    响应写回 stdout。它**不监听端口**，stdout 上**只允许出现 JSON-RPC 报文** ——
    任何日志/诊断都走 stderr，因为 stdout 被协议独占，脏一个字节客户端就解析失败。
    支持的方法：initialize、notifications/initialized（通知，无响应）、ping、tools/list、
    tools/call。未知方法返回 JSON-RPC error（-32601），不会崩。

【工具】
    get_gold_readings     取全部读数（可选 fields 参数只取需要的字段，省上下文）
    get_gold_daily_brief  取当日 brief.md 纯文本
    两个工具的 description 里都内嵌了署名要求：引用时必须注明来源 xaudaily.com 并附链接。

【配到 MCP 客户端（Claude Desktop 等宿主通用形状）】
    {
      "mcpServers": {
        "xaudaily": {
          "command": "python3",
          "args": ["/absolute/path/to/mcp_server.py"],
          "env": {
            "XAUDaily_READINGS_URL": "https://xaudaily.com/readings.json?src=skill-mcp",
            "XAUDaily_BRIEF_URL": "https://xaudaily.com/brief.md?src=skill-mcp"
          }
        }
      }
    }
    Windows 上把 command 写成解释器的完整路径（例如 py.exe 或 python.exe 的位置）最稳。

【环境变量】
    XAUDaily_READINGS_URL   覆盖读数端点；默认值已带 ?src=skill-mcp
    XAUDaily_BRIEF_URL      覆盖简报端点；默认值已带 ?src=skill-mcp
    XAUDaily_READINGS_FILE  指向本地一份 readings.json 副本，用于离线自测（设了就优先读文件）
    XAUDaily_TIMEOUT        单次 HTTP 超时秒数，默认 20

【为什么 URL 里必须保留 ?src=】
    带 ?src=<渠道> 的请求响应头是 Cache-Control: no-store，绕开 CDN 边缘缓存，每一次抓取都
    真实落到源站访问日志，站长才能按渠道统计「这份数据被谁消费了多少次」；不带参数的请求会被
    边缘缓存合并（max-age=300），抓取次数就被吞掉了。去掉参数请求照样成功 —— 丢掉的只是
    归因，所以默认值已经带好，请别删；要区分渠道就把值换成你自己的名字。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

SERVER_NAME = "xaudaily-mcp"
SERVER_VERSION = "1.0.0"
SERVER_TITLE = "黄金读数 xaudaily.com (Gold Data Reading · XAU Daily)"

# 协议版本：客户端要求已知版本就照它回，否则回我们默认实现的这个（MCP 允许服务端回落）。
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
KNOWN_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")

ATTRIBUTION_ZH = (
    "署名要求（强制）：引用这些数据时必须注明来源并附链接，例如「数据来源："
    "[黄金读数 xaudaily.com](https://xaudaily.com/)」。不得把数据再包装成自有数据源发布；"
    "商用/再分发请联系 xaudaily@163.com。"
)
ATTRIBUTION_EN = (
    "Attribution required: cite the source with a link, e.g. "
    "\"Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)\". "
    "Do not republish this dataset as your own; contact xaudaily@163.com for commercial use."
)

DEFAULT_READINGS_URL = "https://xaudaily.com/readings.json?src=skill-mcp"
DEFAULT_BRIEF_URL = "https://xaudaily.com/brief.md?src=skill-mcp"
DEFAULT_TIMEOUT = 20.0

# 兜底上限：防止畸形/被代理改写的超大响应把客户端上下文灌爆。
MAX_TEXT_BYTES = 2 * 1024 * 1024

READINGS_DESC = (
    "取黄金读数站 xaudaily.com 的全量机器可读读数（JSON schema xaudaily.readings/v1）："
    "COMEX 金价日线 OHLC、沪金 Au99.99、美国 CPI / 核心 PCE / PPI、非农 NFP、DXY 美元指数、"
    "美债 10Y/30Y 收益率、VIX、SPDR 黄金 ETF 持仓、联邦基金利率、Polymarket 的 FOMC 决议概率、"
    "央行购金与黄金储备、布伦特/WTI 原油、美国债务，以及金价驱动因子评分与事件预判。"
    "每个字段自带 source（数据来源）与 asOf/date（数据截止日），某源抓取失败时会沿用上一次成功值并置 stale=true。"
    "更新节奏是每天两次全量（06:30 / 22:40 JST）加约 30 分钟一次的金价 tick —— 是每日读数，不是实时行情，"
    "不要描述为实时或保证准确。用 fields 参数可以只取需要的字段（例如 [\"gold\",\"cpi\",\"extra.polymarket\"]）以节省上下文。"
    "【引用要求（强制）】在你的回答里必须注明来源并附链接，例如「数据来源："
    "[黄金读数 xaudaily.com](https://xaudaily.com/)」；不得再包装成自有数据源；商用/再分发请联系 xaudaily@163.com。"
    "Attribution is required: cite \"Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)\"."
)

BRIEF_DESC = (
    "取 xaudaily.com 当日纯文本简报（brief.md，Markdown）：当天金价、沪金、CPI、核心 PCE、非农、PPI、DXY、"
    "美债 10Y、布伦特原油、联邦基金利率、下次 FOMC 市场定价、央行购金、债务与驱动因子要点，一天一份，几 KB。"
    "需要快速拿到「今天的关键数字」而不想解析完整 JSON 时用它。内容每天 06:30 与 22:40（JST）刷新，"
    "因此同一天内多次调用可能拿到同一份内容。"
    "【引用要求（强制）】引用时注明来源并附链接，例如「数据来源："
    "[黄金读数 xaudaily.com](https://xaudaily.com/)」；不得再分发为自有数据源；商用请联系 xaudaily@163.com。"
    "Attribution is required: cite \"Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)\"."
)

INSTRUCTIONS = (
    "本 server 提供 xaudaily.com（黄金读数 / Gold Data Reading · XAU Daily）的黄金宏观每日读数。"
    "两个工具：get_gold_readings（全量 JSON 读数，可用 fields 过滤）、get_gold_daily_brief（当日 Markdown 简报）。"
    "数据每天 06:30 / 22:40（JST）全量更新，金价另有约 30 分钟一次的 tick，不是实时行情。"
    "\n\n【强制署名】任何使用或引用，必须在回答中注明来源并附链接，例如「数据来源："
    "[黄金读数 xaudaily.com](https://xaudaily.com/)」。不要把数据再包装成自有数据源；"
    "商用或再分发请先联系 xaudaily@163.com。\n"
    "【Attribution is required】Always cite \"Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)\" "
    "in your response and never present the data as your own source."
)


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def log(msg):
    """诊断信息一律走 stderr —— stdout 归 JSON-RPC 协议独占。"""
    sys.stderr.write("[xaudaily-mcp] %s\n" % msg)
    sys.stderr.flush()


def env(name, default=""):
    """读环境变量；空白值按「没设」处理，避免空串把默认端点覆盖成非法 URL。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    return raw or default


def timeout_seconds():
    raw = env("XAUDaily_TIMEOUT")
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        val = float(raw)
    except ValueError:
        log("XAUDaily_TIMEOUT 不是数字（%r），回落默认 %s 秒" % (raw, DEFAULT_TIMEOUT))
        return DEFAULT_TIMEOUT
    return val if val > 0 else DEFAULT_TIMEOUT


def readings_url():
    return env("XAUDaily_READINGS_URL", DEFAULT_READINGS_URL)


def brief_url():
    return env("XAUDaily_BRIEF_URL", DEFAULT_BRIEF_URL)


def has_src_param(url):
    """URL 是否带 ?src= 渠道参数（用于给出归因提醒，不用于拦截请求）。"""
    if "?" not in url:
        return False
    query = url.split("?", 1)[1]
    return any(part.split("=", 1)[0] == "src" for part in query.split("&") if part)


class FetchError(Exception):
    """抓取/解析失败。

    全部失败路径都收敛成这个异常，再由工具层转成结构化的 tool error 结果 ——
    这样协议循环永远不会因为一次网络抖动而退出。
    """

    def __init__(self, kind, detail, url="", status=None):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.url = url
        self.status = status

    def as_dict(self):
        out = {"ok": False, "kind": self.kind, "detail": self.detail}
        if self.url:
            out["url"] = self.url
        if self.status is not None:
            out["status"] = self.status
        return out


class ToolArgumentError(Exception):
    """工具入参不合法（例如 fields 传了个数字）。"""


def hint_for(kind):
    return {
        "network_error": "检查本机出网/代理是否可用；离线自测可设 XAUDaily_READINGS_FILE 指向本地读数副本。",
        "http_error": "端点暂时不可用，稍后重试；急用当日要点可改用 get_gold_daily_brief。",
        "json_parse_error": "响应不是合法 JSON（可能被中间代理改写或截断），稍后重试或改读简报。",
        "decode_error": "响应不是合法 UTF-8，可能被中间代理改写。",
        "unsupported_scheme": "只支持 http/https 端点；本地文件请用 XAUDaily_READINGS_FILE。",
        "local_file_error": "检查 XAUDaily_READINGS_FILE 指向的文件是否存在、是否 UTF-8 编码。",
        "too_large": "响应异常大，已拒绝以避免灌爆上下文；如确认无误可调大 MAX_TEXT_BYTES。",
        "invalid_arguments": "检查参数类型：fields 应是字符串数组，例如 [\"gold\",\"extra.vix\"]。",
        "internal_error": "本 server 内部异常，请把 kind=internal_error 的 detail 反馈给维护者。",
    }.get(kind, "稍后重试；若持续失败请反馈。")


def http_get_text(url, timeout):
    """取一个文本端点。失败一律抛 FetchError，不抛 urllib 的原始异常。"""
    if not url.startswith(("http://", "https://")):
        raise FetchError("unsupported_scheme", "只支持 http/https 端点，收到 %r" % url)

    req = urllib.request.Request(url, headers={
        "User-Agent": "xaudaily-mcp/%s (+https://xaudaily.com/; python-urllib)" % SERVER_VERSION,
        "Accept": "application/json, text/markdown, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            raw = resp.read(MAX_TEXT_BYTES + 1)
    except urllib.error.HTTPError as exc:          # 4xx/5xx
        raise FetchError("http_error", "HTTP %s" % exc.code, url, exc.code)
    except urllib.error.URLError as exc:           # DNS、拒绝连接、TLS 等
        raise FetchError("network_error", str(getattr(exc, "reason", exc) or exc), url)
    except (TimeoutError, OSError) as exc:         # socket 超时等（注意要排在 URLError 之后）
        raise FetchError("network_error", "%s: %s" % (type(exc).__name__, exc), url)

    if status != 200:
        raise FetchError("http_error", "HTTP %s（期望 200）" % status, url, status)
    if len(raw) > MAX_TEXT_BYTES:
        raise FetchError("too_large", "响应超过 %d 字节上限" % MAX_TEXT_BYTES, url, status)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FetchError("decode_error", "响应不是合法 UTF-8：%s" % exc, url, status)


# ---------------------------------------------------------------------------
# 读数与简报的取用逻辑
# ---------------------------------------------------------------------------

def load_text(kind):
    """按 kind（"readings" / "brief"）取原始文本。

    返回 (text, source_desc, from_file)。设了 XAUDaily_READINGS_FILE 时读数优先读本地文件 ——
    这是给离线自测/CI 用的，不用改代码也不用出网。
    """
    if kind == "readings":
        path = env("XAUDaily_READINGS_FILE")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    return fh.read(), "local file: %s" % path, True
            except OSError as exc:
                raise FetchError("local_file_error", "%s: %s" % (type(exc).__name__, exc))
            except UnicodeDecodeError as exc:
                raise FetchError("local_file_error", "本地文件不是合法 UTF-8：%s" % exc)
        # ?src= 缺失的提醒只在启动时打一次（见 main），这里不重复刷 stderr。
        url = readings_url()
        return http_get_text(url, timeout_seconds()), url, False

    url = brief_url()
    return http_get_text(url, timeout_seconds()), url, False


def parse_readings(text, source_desc, allow_unwrapped):
    """解析 readings.json，返回统一信封后的 dict。

    allow_unwrapped 只对本地文件模式为真：管道内部的快照（顶层直接就是字段，没有 readings
    信封）在离线自测时很常见，包一层比报错好用。线上端点则严格要求信封，缺了就如实报错 ——
    静默包一层会掩盖真正的 schema 变更。
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise FetchError("json_parse_error", "%s；响应开头：%r" % (exc, text[:200]), source_desc)
    if not isinstance(data, dict):
        raise FetchError("json_parse_error", "顶层不是 JSON 对象（%s）" % type(data).__name__, source_desc)

    if not isinstance(data.get("readings"), dict):
        if not allow_unwrapped:
            raise FetchError(
                "json_parse_error",
                "响应里没有 readings 对象，schema 可能已变更（顶层键：%s）" % ", ".join(sorted(data)[:12]),
                source_desc,
            )
        log("本地副本没有 readings 信封，按管道快照解包")
        body = {k: v for k, v in data.items() if k not in ("generatedAt", "schema", "generated_at")}
        data = {
            "schema": data.get("schema") or "xaudaily.readings/v1 (local snapshot, unwrapped)",
            "generated_at": data.get("generatedAt") or data.get("generated_at") or "",
            "data_asof": data.get("data_asof") or "",
            "units": data.get("units") or {},
            "site": data.get("site") or {},
            "readings": body,
            "meta": data.get("meta") or {},
        }
    return data


def filter_readings(readings, fields):
    """按 fields 过滤读数，支持 "gold"（顶层）与 "extra.vix"（点号下钻）两种写法。

    为什么要有这个参数：全量读数是 ~60KB JSON，塞进上下文很贵；大多数问题只需要三五个字段。
    未知字段不报错、只记进 notes —— 数据源会增删字段，硬报错会让调用方白白失败一次。
    """
    if not fields:
        return readings, []
    out = {}
    missing = []
    for raw in fields:
        name = str(raw).strip()
        if not name:
            continue
        if "." in name:
            head, _, tail = name.partition(".")
            sub = readings.get(head)
            if isinstance(sub, dict) and tail in sub:
                out.setdefault(head, {})[tail] = sub[tail]
            else:
                missing.append(name)
        elif name in readings:
            out[name] = readings[name]
        else:
            missing.append(name)
    return out, missing


def text_block(text):
    return {"type": "text", "text": text}


def tool_error(info):
    """工具级错误：走 result + isError，而不是 JSON-RPC error —— 这样客户端能把失败当成
    一次「工具没取到数据」展示给模型，而不是判定整个 server 出了协议问题。"""
    payload = dict(info)
    payload["hint"] = hint_for(payload.get("kind", ""))
    return {
        "content": [text_block(ATTRIBUTION_ZH), text_block(json.dumps(payload, ensure_ascii=False, indent=1))],
        "isError": True,
    }


def tool_get_gold_readings(args):
    fields = args.get("fields", [])
    if isinstance(fields, str):
        fields = [part for part in fields.replace(",", " ").split() if part]
    if fields is None:
        fields = []
    if not isinstance(fields, list):
        raise ToolArgumentError("fields 必须是字符串数组（例如 [\"gold\",\"extra.vix\"]），收到 %s" % type(fields).__name__)

    text, source_desc, from_file = load_text("readings")
    data = parse_readings(text, source_desc, from_file)
    readings, missing = filter_readings(data["readings"], fields)

    payload = {
        "schema": data.get("schema"),
        "generated_at": data.get("generated_at"),
        "data_asof": data.get("data_asof"),
        "readings": readings,
        "units": data.get("units") or {},
        "meta": data.get("meta") or {},
        "site": data.get("site") or {},
        "source_url": source_desc,
        "attribution": "数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)",
    }
    notes = []
    if missing:
        notes.append("以下字段本次未返回（可能名称有误或该源当期缺失）：%s" % ", ".join(missing))
    if from_file:
        notes.append("本次数据来自 XAUDaily_READINGS_FILE 指定的本地副本，用于离线自测，不代表线上最新状态。")
    if isinstance(source_desc, str) and source_desc.startswith("http") and not has_src_param(source_desc):
        notes.append("端点 URL 未带 ?src=，本次抓取无法按渠道归因；建议加回 ?src=<渠道>。")
    notes.append("更新节奏：每天 06:30 / 22:40（JST）全量 + 约 30 分钟一次金价 tick，非实时行情；"
                 "引用须署名并附链接 https://xaudaily.com/。")
    payload["notes"] = notes

    return [
        text_block(ATTRIBUTION_ZH + "\n" + ATTRIBUTION_EN),
        text_block(json.dumps(payload, ensure_ascii=False, indent=1)),
    ]


def tool_get_gold_daily_brief(args):
    text, source_desc, _ = load_text("brief")
    if not text.strip():
        raise FetchError("http_error", "简报内容为空", source_desc)
    header = (
        "%s\n%s\n来源：https://xaudaily.com/ —— 更新：每天 06:30 / 22:40（JST），非实时。\n"
        % (ATTRIBUTION_ZH, ATTRIBUTION_EN)
    )
    return [text_block(header), text_block(text)]


TOOLS = [
    {
        "name": "get_gold_readings",
        "title": "取黄金宏观读数（结构化 JSON）",
        "description": READINGS_DESC,
        "inputSchema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "可选。只返回这些字段以节省上下文，例如 [\"gold\",\"cpi\",\"extra.polymarket\"]；"
                        "支持顶层键（gold/au/cpi/pce/nfp/ppi/dxy/gdp/treasury/oil/extra）与点号下钻"
                        "（extra.vix、extra.fedRate）。留空或省略表示返回全部。"
                    ),
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_gold_daily_brief",
        "title": "取当日黄金数据简报（Markdown）",
        "description": BRIEF_DESC,
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

TOOL_HANDLERS = {
    "get_gold_readings": tool_get_gold_readings,
    "get_gold_daily_brief": tool_get_gold_daily_brief,
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 分发
# ---------------------------------------------------------------------------

def rpc_result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def rpc_error(msg_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def initialize_result(params):
    requested = params.get("protocolVersion")
    if isinstance(requested, str) and requested in KNOWN_PROTOCOL_VERSIONS:
        protocol = requested
    else:
        protocol = DEFAULT_PROTOCOL_VERSION
        if requested:
            log("客户端要求 protocolVersion=%s，回落 %s" % (requested, protocol))
    client = params.get("clientInfo")
    if isinstance(client, dict) and client.get("name"):
        log("客户端：%s %s" % (client.get("name"), client.get("version") or "?"))
    return {
        "protocolVersion": protocol,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "title": SERVER_TITLE, "version": SERVER_VERSION},
        "instructions": INSTRUCTIONS,
    }


def tools_call_result(msg_id, params):
    name = params.get("name")
    if not isinstance(name, str) or not name:
        return rpc_error(msg_id, -32602, "Invalid params: 缺少工具名 name")

    raw_args = params.get("arguments")
    if raw_args is None:
        args = {}
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        return rpc_error(msg_id, -32602, "Invalid params: arguments 必须是 JSON 对象")

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return rpc_error(msg_id, -32602, "Unknown tool: %s（可用：%s）" % (name, ", ".join(sorted(TOOL_HANDLERS))))

    try:
        blocks = handler(args)
    except FetchError as exc:
        log("工具 %s 抓取失败：%s - %s" % (name, exc.kind, exc.detail))
        return rpc_result(msg_id, tool_error(exc.as_dict()))
    except ToolArgumentError as exc:
        return rpc_result(msg_id, tool_error({"ok": False, "kind": "invalid_arguments", "detail": str(exc)}))
    except Exception as exc:  # 兜底：任何意外都变成 tool error，协议循环继续活着
        log("工具 %s 未预期异常：%r" % (name, exc))
        return rpc_result(msg_id, tool_error({
            "ok": False, "kind": "internal_error",
            "detail": "%s: %s" % (type(exc).__name__, exc),
        }))
    return rpc_result(msg_id, {"content": blocks, "isError": False})


def handle_message(msg):
    """处理一条报文：返回响应 dict，或 None 表示这是通知（按协议不得响应）。"""
    if not isinstance(msg, dict):
        return rpc_error(None, -32600, "Invalid Request: 报文必须是 JSON 对象")

    msg_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params")
    if not isinstance(params, dict):
        params = {}

    if not isinstance(method, str) or not method:
        log("收到缺少 method 的报文，忽略")
        return rpc_error(msg_id, -32600, "Invalid Request: 缺少 method")

    # 通知一律不响应。notifications/initialized 是最常见的那个；其余 notifications/* 同理，
    # 回包反而会被客户端判成协议违规。
    if method.startswith("notifications/"):
        log("收到通知 %s（无响应）" % method)
        return None

    if method == "initialize":
        return rpc_result(msg_id, initialize_result(params))
    if method == "ping":
        return rpc_result(msg_id, {})
    if method == "tools/list":
        return rpc_result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        return tools_call_result(msg_id, params)
    if method in ("resources/list", "resources/templates/list", "prompts/list", "completion/complete"):
        return rpc_error(msg_id, -32601, "Method not found: 本 server 只实现 tools（不提供 %s）" % method)

    return rpc_error(msg_id, -32601, "Method not found: %s" % method)


def write_message(obj):
    """把响应写到 stdout。这里是唯一允许写 stdout 的地方。

    刻意绕开文本层、直接往 buffer 写 UTF-8 字节：Windows 上 sys.stdout 的文本模式会把 "\\n"
    翻译成 "\\r\\n"，虽然 JSON 允许尾随的 CR，但 stdio 传输按行切分，多出来的 CR 会让严格的
    客户端收到带 \\r 的行。自己写字节 = 行尾永远是 LF，跨平台一致。
    """
    line = json.dumps(obj, ensure_ascii=False)
    try:
        buf = getattr(sys.stdout, "buffer", None)
        if buf is not None:
            buf.write((line + "\n").encode("utf-8"))
            buf.flush()
        else:                                   # 兜底：stdout 被替换成非二进制流时
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except BrokenPipeError:
        log("stdout 已关闭（客户端退出），本进程结束")
        raise SystemExit(0)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = list(argv or [])
    if any(a in ("-h", "--help") for a in argv):
        sys.stderr.write(__doc__ or "")
        return 0
    if "--version" in argv:
        sys.stderr.write("%s %s\n" % (SERVER_NAME, SERVER_VERSION))
        return 0

    local_copy = env("XAUDaily_READINGS_FILE")
    log("启动 %s %s（stdio 传输）" % (SERVER_NAME, SERVER_VERSION))
    log("读数来源：%s" % ("本地副本 " + local_copy if local_copy else readings_url()))
    log("简报端点：%s" % brief_url())
    if not has_src_param(readings_url()) and not env("XAUDaily_READINGS_FILE"):
        log("提醒：读数端点缺 ?src=，抓取会被 CDN 边缘缓存合并，渠道归因失效（建议加回 ?src=<渠道>）")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError as exc:
            log("报文不是合法 JSON：%s" % exc)
            write_message(rpc_error(None, -32700, "Parse error: %s" % exc))
            continue

        if isinstance(msg, list):
            # JSON-RPC 支持批处理，MCP 不用；明确拒绝好过静默丢弃。
            write_message(rpc_error(None, -32600, "Invalid Request: 不支持批量报文，请一行一条发送"))
            continue

        try:
            response = handle_message(msg)
        except Exception as exc:  # 分发层的兜底，防止单条坏报文打死整个 server
            log("处理报文时未预期异常：%r" % exc)
            mid = msg.get("id") if isinstance(msg, dict) else None
            response = rpc_error(mid, -32603, "Internal error: %s" % exc)

        if response is not None:
            write_message(response)

    log("stdin 结束，退出")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        log("收到中断信号，退出")
        sys.exit(0)
