# Polymarket 结构性套利扫描器

只读、无需 API key。用 Polymarket 公开的 Gamma API(市场列表/报价)和 CLOB API
(订单簿)扫描两类结构性错价:

1. **neg-risk 套利**:互斥多结果事件中,买齐所有 YES 的成本 < $1(或买齐所有
   NO 的成本 < $N-1),无风险锁定差价。
2. **交叉盘口**:单个二元市场 YES ask + NO ask < $1。

候选先用 Gamma 顶档价格筛出,再拉完整订单簿做**深度感知的模拟成交**
(资金上限 $2000),记录的是当时真正可执行的利润,不是顶档幻觉。

## 用法

```bash
python3 scanner.py             # 单次实盘扫描,结果追加到 data/*.jsonl
python3 scanner.py --selftest  # 用合成订单簿验证检测与利润计算
python3 report.py              # 汇总 data/ 生成 REPORT.md
```

## 数据文件(追加式 JSONL)

- `data/scans.jsonl` — 每次扫描一行:覆盖面、候选数、可执行机会数、纸面利润
- `data/opportunities.jsonl` — 每个经订单簿验证的机会,含模拟成交明细
- `data/near_misses.jsonl` — 价格和在 1.00–1.02 之间的"近失"事件

## 网络要求

需要访问 `gamma-api.polymarket.com` 与 `clob.polymarket.com`。
在 Claude Code 远程环境里,这两个域名默认可能被环境网络策略拦截
(表现为 CONNECT 403 / EGRESS_BLOCKED)——需在 claude.ai/code 的环境设置中
把它们加入允许域名,或选择放开的网络策略。被拦截的扫描会记录为
`status: "network_error"`,不会污染数据。
