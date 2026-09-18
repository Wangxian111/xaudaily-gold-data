# 今日金价徽标（badge）· 嵌入说明

由 **黄金读数 / Gold Data Reading · XAU Daily**（<https://xaudaily.com/>）提供的可嵌入金价徽标。
一行代码贴到网站、博客、导航页或 GitHub README，即可显示 COMEX 金价（XAU，美元/盎司）与
沪金 Au99.99（元/克）的最新价与日涨跌。**徽标图由本站托管并每日自动更新**，粘贴一次即可长期使用。

- 浅色版：`https://xaudaily.com/widget/gold-badge.svg`（320×96）
- 深色版：`https://xaudaily.com/widget/gold-badge-dark.svg`（320×96）
- 当前数据：XAU 4,454.7 USD/oz（日涨跌 -0.50%） · 沪金暂无数据 · 数据截至 2026-09-07

## 1. 快速嵌入

### GitHub README / 支持 Markdown 的站点

```markdown
[![黄金读数 XAU Daily 今日金价](https://xaudaily.com/widget/gold-badge.svg)](https://xaudaily.com/?utm_source=widget&utm_medium=embed&utm_campaign=gold-badge)
```

### 网站 HTML（浅色主题）

```html
<a href="https://xaudaily.com/?utm_source=widget&utm_medium=embed&utm_campaign=gold-badge" target="_blank" rel="noopener"
   title="黄金读数 XAU Daily · 今日金价">
  <img src="https://xaudaily.com/widget/gold-badge.svg" width="320" height="96"
       alt="黄金读数 XAU Daily 今日金价徽标" loading="lazy">
</a>
```

### 网站 HTML（深色主题）

```html
<a href="https://xaudaily.com/?utm_source=widget&utm_medium=embed&utm_campaign=gold-badge" target="_blank" rel="noopener"
   title="黄金读数 XAU Daily · 今日金价">
  <img src="https://xaudaily.com/widget/gold-badge-dark.svg" width="320" height="96"
       alt="黄金读数 XAU Daily 今日金价徽标（深色）" loading="lazy">
</a>
```

## 2. 嵌入注意事项（重要）

1. **SVG 内部的链接不可点击，必须用外层 `<a>` 包裹 `<img>`。**
   通过 `<img src="…gold-badge.svg">` 加载的 SVG 是「被动图片」，其内部 `<a>` 不响应点击、
   光标也不是手型（浏览器安全模型如此）。所以徽标**内部只显示** `xaudaily.com` 作为可见署名，
   可点击链接一律由外层 `<a>` 提供。请使用上面的完整写法，不要只贴一个孤立的 `<img>`。
2. **请保留 UTM 参数**：`?utm_source=widget&utm_medium=embed&utm_campaign=gold-badge`。
   上面代码块里的链接用的是原始 `&` —— 这样贴进 Markdown 或 HTML 都不会被二次转义
   （若你的 HTML 校验器要求转义，写成 `&amp;` 也一样可用）。删掉参数链接仍能打开，
   但挂件流量就没法归因了。
3. **不要下载后自行托管**。徽标每日重新生成，自托管会一直显示你下载那天的旧图。
4. **不要裁剪 / 遮挡署名**。右下角的 `xaudaily.com` 与数据截止日是署名，可整体缩放，
   但请勿裁掉或用 CSS 隐藏。
5. **建议带上 `width`/`height`**（或 CSS 宽高），避免图片加载时页面布局跳动。
   徽标是固定 320×96 的矢量图，缩放不失真。
6. 徽标是纯静态图片，不依赖 JS，也没有跨域（CORS）问题。

## 3. 配色约定：红涨绿跌

徽标沿用本站配色：**红色 = 上涨，绿色 = 下跌**，即**中国用户习惯**（与国际市场「绿涨红跌」相反）。
徽标内同时使用 `▲` / `▼` 箭头辅助表达方向。

- 面向中文读者的站点：可直接嵌入。
- 面向英文 / 国际读者的站点：请在嵌入处补一句说明（如 “red = up, green = down, China convention”），
  或不要把徽标当作涨跌方向的唯一提示。

## 4. 数据口径与缺失值

| 字段 | 口径 |
| --- | --- |
| XAU | COMEX GC 黄金连续合约，美元/盎司（日线，盘中可含实时 tick） |
| 沪金 | 上海黄金交易所 SGE Au99.99 连续（现货），元/克（CNY/g） |
| 日涨跌 | 最新价相对前一交易日收盘（或实时 tick 相对昨收）的百分比变化 |
| 更新频率 | 每日自动管道更新，盘中实时 tick 会同步刷新 |
| 缺失值 | 数据源不可用时该字段显示 `—`，绝不显示过期数字 |

仅供研究与信息参考，不构成投资建议；不保证数据完整性或准确性，请以交易所与官方机构公布数值为准。

## 5. 署名与许可

可免费用于任何网站、文档与开源项目，无需申请。仅两条要求：
保留徽标内可见的 `xaudaily.com` 署名；外层链接指向 <https://xaudaily.com/> 并保留 UTM 参数。
