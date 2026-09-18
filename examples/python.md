# Python 示例（只用标准库，可直接复制运行）

Python 3.8+，不需要 `pip install` 任何东西。所有 URL 都带 `?src=skill-github`——**请保留这个参数**（换成你自己的渠道名也行）：带 `?src=` 的请求响应头是 `Cache-Control: no-store`，绕开 CDN 边缘缓存，每次抓取都真实落到源站日志；去掉后抓取次数会被边缘缓存合并，渠道归因失效。理由详见仓库 `README.md`。

## 1. 最小读取

```python
import json
import urllib.request

URL = "https://xaudaily.com/readings.json?src=skill-github"   # 别去掉 ?src=

with urllib.request.urlopen(URL, timeout=20) as resp:
    data = json.load(resp)          # 响应是 UTF-8 的 application/json

print(data["schema"])               # xaudaily.readings/v1
print(data["generated_at"], "| 数据截止", data["data_asof"])

r = data["readings"]
print("COMEX 最新日线收盘:", r["gold"]["rows"][-1]["c"], r["gold"]["rows"][-1]["d"], r["gold"]["unit"])
print("沪金:", r["au"].get("last"), r["au"]["unit"], r["au"]["asOf"])
print("CPI 同比:", r["cpi"]["vals"][-1], "%  ", r["cpi"]["months"][-1])

print("数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)")   # 引用必须署名
```

## 2. 处理「异构字段」的通用取数函数

读数里每个字段的载荷形状不同（`gold` 是日线 `rows`、`cpi` 是 `months`+`vals` 平行数组、`gdp` 是 `quarters` 对象数组、`extra.vix` 是单值）。与其给每个字段写一套解析，不如按统一约定写一个函数，把三种形状全兜住：

```python
def latest_point(field):
    """返回 (标签, 值)。标签通常是数据期（'2026-08' 或 '2026-09-18'）。

    三种形状：
      1) 单值：extra.vix / extra.spdr 用 value + date；extra.fedRate 同时有 value 和
         months/vals 历史，优先取 value/date（当期值比历史序列的最后一格更准）
      2) 两个平行数组：months / dates + vals
      3) 对象数组：gdp 的 quarters / real，元素形如 {"q": "2026-Q2", "val": 1.5}；
         gold 的 rows 同理，元素形如 {"d": "...", "c": 4404.9}
    取不到就返回 (None, None)，绝不抛异常 —— 上游加删字段时不该让你的脚本崩掉。
    """
    if not isinstance(field, dict):
        return None, None
    if "value" in field:
        return field.get("date"), field.get("value")
    for labels_key in ("months", "dates"):
        labels, values = field.get(labels_key), field.get("vals")
        if isinstance(labels, list) and isinstance(values, list) and values:
            n = min(len(labels), len(values))   # 理论上等长，取 min 只是为了不越界
            return labels[n - 1], values[n - 1]
    for seq_key in ("quarters", "real", "rows"):
        seq = field.get(seq_key)
        if isinstance(seq, list) and seq and isinstance(seq[-1], dict):
            last = seq[-1]
            label = last.get("q") or last.get("d") or last.get("date")
            value = last["val"] if "val" in last else last.get("c")
            if label is not None or value is not None:
                return label, value
    return None, None
```

## 3. 完整脚本：抓一份读数，打印带署名的 Markdown 摘要

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""取一份 xaudaily.com 黄金读数，打印可直接粘进笔记的 Markdown 摘要。只用标准库。"""

import json
import urllib.error
import urllib.request

READINGS_URL = "https://xaudaily.com/readings.json?src=skill-github"   # 保留 ?src=
SITE = "https://xaudaily.com/"
TIMEOUT = 20


def fetch_json(url, timeout=TIMEOUT):
    """取 JSON。超时/网络错误/非 200 都收敛成 RuntimeError，好让调用方决定怎么降级。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "gold-readings-example/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if status != 200:
                raise RuntimeError("HTTP %s（期望 200）" % status)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("HTTP %s：端点暂时不可用，稍后重试" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("网络不可达：%s" % getattr(exc, "reason", exc)) from exc
    except ValueError as exc:                    # JSON 解析失败
        raise RuntimeError("响应不是合法 JSON：%s" % exc) from exc


def latest_point(field):
    """(标签, 值) —— 平行数组 / 对象数组 / 单值三种形状，见上文第 2 节。"""
    if not isinstance(field, dict):
        return None, None
    if "value" in field:
        return field.get("date"), field.get("value")
    for labels_key in ("months", "dates"):
        labels, values = field.get(labels_key), field.get("vals")
        if isinstance(labels, list) and isinstance(values, list) and values:
            n = min(len(labels), len(values))
            return labels[n - 1], values[n - 1]
    for seq_key in ("quarters", "real", "rows"):
        seq = field.get(seq_key)
        if isinstance(seq, list) and seq and isinstance(seq[-1], dict):
            last = seq[-1]
            label = last.get("q") or last.get("d") or last.get("date")
            value = last["val"] if "val" in last else last.get("c")
            if label is not None or value is not None:
                return label, value
    return None, None


def fomc_odds(poly):
    """Polymarket 的概率是 0~1 的小数，展示时乘 100；缺键就不显示。"""
    if not isinstance(poly, dict):
        return "无"
    parts = []
    for key, name in (("cut50", "降息50bp"), ("cut25", "降息25bp"), ("hold", "不变"),
                      ("hike25", "加息25bp"), ("hike50", "加息50bp")):
        val = poly.get(key)
        if isinstance(val, (int, float)):
            parts.append("%s %.1f%%" % (name, val * 100))
    return " / ".join(parts) if parts else "无"


def drivers_top(data, n=3):
    """驱动因子评分：-100 利空 ~ +100 利多。"""
    rows = (data.get("readings", {}).get("extra") or {}).get("drivers")
    if not isinstance(rows, list):
        return []
    ranked = [d for d in rows if isinstance(d, dict) and isinstance(d.get("score"), (int, float))]
    ranked.sort(key=lambda d: abs(d["score"]), reverse=True)
    return ranked[:n]


def main():
    data = fetch_json(READINGS_URL)
    r = data["readings"]
    units = data.get("units") or {}

    def stale_mark(field):
        # stale=true 表示该源本次抓取失败、数值沿用上一次成功值 —— 引用时要如实说明
        return " ⚠️stale" if isinstance(field, dict) and field.get("stale") else ""

    lines = ["## 黄金读数速览（数据源 xaudaily.com）", ""]
    lines.append("- 抓取时间：%s ｜ 数据基准：%s" % (data.get("generated_at"), data.get("data_asof")))

    d, c = latest_point(r.get("gold"))
    if c is not None:
        lines.append("- COMEX GC 连续：%s %s（%s）" % (c, (r.get("gold") or {}).get("unit") or units.get("gold", ""), d))
    au = r.get("au") or {}
    if au.get("last") is not None:
        lines.append("- 沪金 Au99.99：%s %s（%s，日涨跌 %s%%）"
                     % (au.get("last"), au.get("unit", units.get("au", "")), au.get("asOf"), au.get("chg1d")))

    for key, name in (("cpi", "CPI 同比"), ("pce", "核心 PCE 同比"), ("nfp", "非农新增"),
                      ("ppi", "PPI 同比"), ("dxy", "美元指数"), ("gdp", "实际 GDP")):
        field = r.get(key)
        d, v = latest_point(field)
        if v is not None:
            lines.append("- %s：%s（%s）%s" % (name, v, d, stale_mark(field)))

    for path, name in ((("extra", "vix"), "VIX"), (("extra", "spdr"), "SPDR 黄金 ETF 持仓（吨）"),
                       (("extra", "fedRate"), "联邦基金利率上限")):
        d, v = latest_point((r.get(path[0]) or {}).get(path[1]))
        if v is not None:
            lines.append("- %s：%s（%s）" % (name, v, d))

    odds = fomc_odds((r.get("extra") or {}).get("polymarket"))
    if odds != "无":
        lines.append("- 下次 FOMC 市场定价（Polymarket）：%s" % odds)

    top = drivers_top(data)
    if top:
        lines.append("- 驱动因子（按强度）：" + "；".join(
            "%s %+d" % (t.get("name") or t.get("nameEn"), t["score"]) for t in top))

    lines += ["", "不构成投资建议。", "",
              "数据来源：[黄金读数 xaudaily.com](%s)（CC-BY-4.0，引用请署名并附链接）" % SITE]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
```

## 4. 只要一段纯文本简报

```python
import urllib.request

URL = "https://xaudaily.com/brief.md?src=skill-github"    # 几 KB，当天关键数字

with urllib.request.urlopen(URL, timeout=20) as resp:
    brief = resp.read().decode("utf-8")

print(brief)
print("数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)")
```

## 5. 离线自测：不联网也能跑

先把线上那份存成本地副本，然后在代码里优先读文件：

```python
import json
import os
import urllib.request

LOCAL = os.environ.get("XAUDaily_READINGS_FILE")      # 例如 ./readings.json
URL = "https://xaudaily.com/readings.json?src=skill-github"

if LOCAL and os.path.exists(LOCAL):
    with open(LOCAL, encoding="utf-8") as fh:
        data = json.load(fh)
else:
    with urllib.request.urlopen(URL, timeout=20) as resp:
        data = json.load(resp)

# 管道内部的快照（顶层直接就是字段、没有 readings 信封）也能兜住
readings = data.get("readings") or {k: v for k, v in data.items() if k != "generatedAt"}
print("字段:", ", ".join(readings.keys()))
```

## 6. 几件该注意的事

1. **保留 `?src=`**：这是上游能按渠道统计「被消费了多少次」的唯一依据。
2. **`gold` 没有 `last`**：`gold` 是 `rows`（日线 OHLC）数组，最新价用 `rows[-1].c`；`live` 可能出现也可能不出现，**以实际返回为准**。
3. **`vals` 与 `months` 按下标配对**：不是 `{月份: 数值}` 字典；`dates`/`vals`（`dxy`、`vixs`、`treasury.y10`）同理。但 `gdp` 的 `quarters`/`real` 是**对象数组**（`{"q": "2026-Q2", "val": 1.5}`），`gold` 的 `rows` 也是对象数组（`{"d","o","h","l","c"}`）——别拿一套解析硬套。
4. **`stale: true` 要如实转述**：说明「该字段数据源本次未更新」或干脆不用它。
5. **概率是 0~1**：`extra.polymarket` 的 `hike25`/`hold`/`cut25` 等要乘 100 才是百分比，且它们是市场定价而非本站预测。
6. **单位看 `units`**：美债是 %，原油是美元/桶，非农是万人，SPDR 是吨，沪金是元/克。
7. **别比 5 分钟更勤地抓**：正常缓存头是 `max-age=300`；一次全量拉取（约 60 KB）本地筛字段，比反复请求更省事。
8. **不要描述成「实时」「保证准确」**：它是每日两次全量更新（06:30 / 22:40 JST）加约 30 分钟一次的金价 tick。
9. **输出必须署名**：`数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)`；不得再包装成自有数据源；商用/再分发请联系 `xaudaily@163.com`。
