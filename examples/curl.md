# curl 示例（可直接复制运行）

所有 URL 都带 `?src=<渠道>`。示例统一用 `skill-github`；**请保留这个参数**（换成你自己的渠道名也可以）——带 `?src=` 的请求响应头是 `Cache-Control: no-store`，会绕开 CDN 边缘缓存，让每一次抓取都真实落到源站日志；去掉之后抓取次数会被边缘缓存合并，渠道归因就没了。详见仓库 `README.md`。

## 1. 全量读数（约 60 KB）

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' -o readings.json
```

看一眼响应头（确认类型与缓存策略）：

```bash
curl -sSI 'https://xaudaily.com/readings.json?src=skill-github'
# Content-Type: application/json
# Cache-Control: no-store           ← 因为带了 ?src=（不带则是 public, max-age=300）
```

别名端点（同一个文件，给习惯 `latest` 的客户端）：

```bash
curl -sS 'https://xaudaily.com/latest.json?src=skill-github' -o latest.json
```

## 2. 先看元信息，再看数据

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("schema:", d["schema"]); print("generated_at:", d["generated_at"]); print("data_asof:", d["data_asof"]); print("字段:", ", ".join(d["readings"].keys())); print("extra:", ", ".join(d["readings"]["extra"].keys()))'
```

顺手做一次结构自检（schema 对不对、`vals` 与 `months` 是否等长）：

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["schema"]=="xaudaily.readings/v1", d["schema"]; r=d["readings"]; assert len(r["gold"]["rows"])>0; assert len(r["cpi"]["vals"])==len(r["cpi"]["months"]); print("OK", d["generated_at"])'
```

## 3. 取几个关键数字

```bash
# 金价（日线最后一根收盘）、沪金、CPI 同比
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["readings"]; g=r["gold"]["rows"][-1]; print("COMEX", g["c"], r["gold"]["unit"], "(" + g["d"] + ")"); print("沪金", r["au"].get("last"), r["au"]["unit"], "(" + r["au"]["asOf"] + ")"); print("CPI", r["cpi"]["vals"][-1], "%", "(" + r["cpi"]["months"][-1] + ")")'
```

如果本机装了 `jq`，写法更短（注意 `gold` 只有 `rows`，**没有 `last`**）：

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | jq '{generated_at, data_asof, gold_last: .readings.gold.rows[-1], au_last: .readings.au.last, cpi: .readings.cpi.vals[-1], month: .readings.cpi.months[-1], fomc: (.readings.extra.polymarket | {hike25, hold, cut25, cut50})}'
```

## 4. 只取一个字段（省流量也省 token）

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps({"generated_at": d["generated_at"], "gold": d["readings"]["gold"], "polymarket": d["readings"]["extra"]["polymarket"]}, ensure_ascii=False, indent=1))'
```

## 5. 当日纯文本简报（几 KB，可直接进上下文）

```bash
curl -sS 'https://xaudaily.com/brief.md?src=skill-github'
```

## 6. 历史与站点其它入口

```bash
# 全部存档索引（每天一个稳定 URL，历史可回溯）
curl -sS 'https://xaudaily.com/d/?src=skill-github' | head -40

# 某一天的存档页
curl -sS 'https://xaudaily.com/d/2026-09-18.html?src=skill-github' | head -40

# 站点给 LLM 的自述文件 / 专题解读 / sitemap
curl -sS 'https://xaudaily.com/llms.txt?src=skill-github'
curl -sS 'https://xaudaily.com/topic/?src=skill-github' | head -40
curl -sS 'https://xaudaily.com/sitemap.xml?src=skill-github'
```

## 7. 处理降级字段（`stale`）

某字段的 `stale` 为 `true`，表示该数据源本次抓取失败、数值沿用上一次成功值。**别把它当当期最新数据引用**：

```bash
curl -sS 'https://xaudaily.com/readings.json?src=skill-github' \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["readings"]; c=r["cpi"]; print("CPI", c["vals"][-1], c["months"][-1], "stale=", c.get("stale"), "published=", c.get("published"))'
```

## 8. 引用时的署名（输出里务必带）

```markdown
数据来源：[黄金读数 xaudaily.com](https://xaudaily.com/)（数据截止 2026-09-18，本地抓取时间 2026-09-19 00:00 JST）
```

英文场景：

```markdown
Source: [Gold Data Reading · XAU Daily](https://xaudaily.com/)
```

不得把数据再包装成自有数据源；商用/再分发请先联系 `xaudaily@163.com`。

## 9. 一点点礼貌

- 读数响应的正常缓存头是 `max-age=300`（5 分钟）：**不要比 5 分钟更勤地抓**，写完一次就复用。
- `brief.md` 每天只在 06:30 / 22:40（JST）变，一天抓一两次足够。
- 支持一次全量拉取（约 60 KB）然后本地筛字段，比反复请求更省事也更省对方带宽。
