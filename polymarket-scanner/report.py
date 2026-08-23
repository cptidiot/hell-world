#!/usr/bin/env python3
"""Summarize a week of scanner output into polymarket-scanner/REPORT.md."""

import json
import os
import sys
from collections import Counter


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def main(data_dir):
    scans = load_jsonl(os.path.join(data_dir, "scans.jsonl"))
    opps = load_jsonl(os.path.join(data_dir, "opportunities.jsonl"))
    nears = load_jsonl(os.path.join(data_dir, "near_misses.jsonl"))

    ok = [s for s in scans if s.get("status") == "ok"]
    blocked = [s for s in scans if s.get("status") != "ok"]
    total_profit = round(sum(o["fill"]["profit_usd"] for o in opps), 2)
    kinds = Counter(o["kind"] for o in opps)
    near_events = Counter(n.get("event") for n in nears)

    lines = ["# Polymarket 扫描周报", ""]
    if scans:
        lines.append(f"扫描窗口:{scans[0]['ts']} — {scans[-1]['ts']}")
    lines += [
        "",
        "## 覆盖情况",
        "",
        f"- 总扫描次数:{len(scans)}(成功 {len(ok)},失败/被网络策略拦截 {len(blocked)})",
    ]
    if ok:
        avg_mkts = sum(s.get("n_markets_quoted", 0) for s in ok) / len(ok)
        lines.append(f"- 平均每次扫描有报价的市场数:{avg_mkts:.0f}")
        best = min(
            (s["best_negrisk_yes_sum"] for s in ok if s.get("best_negrisk_yes_sum")),
            default=None, key=lambda b: b[0])
        if best:
            lines.append(
                f"- 全周期最低的 neg-risk YES 价格和:{best[0]}(事件:{best[1]},{best[2]} 个结果)"
                "  — 低于 1.00 才存在套利")
    lines += [
        "",
        "## 套利机会(经订单簿深度验证、$2000 资金内可执行)",
        "",
        f"- 发现次数:{len(opps)};理论总利润:**${total_profit}**",
    ]
    for kind, n in kinds.most_common():
        lines.append(f"  - {kind}: {n} 次")
    if opps:
        lines += ["", "| 时间 | 类型 | 事件 | 成本$ | 利润$ | 收益% |",
                  "|---|---|---|---|---|---|"]
        for o in sorted(opps, key=lambda o: -o["fill"]["profit_usd"])[:15]:
            lines.append(
                f"| {o['ts']} | {o['kind']} | {(o.get('event') or '')[:50]} "
                f"| {o['fill']['cost_usd']} | {o['fill']['profit_usd']} "
                f"| {o['fill'].get('return_pct', '')} |")
    lines += [
        "",
        "## 近失机会(价格和在 1.00–1.02 之间,尚无利润但值得盯)",
        "",
        f"- 记录条数:{len(nears)},涉及事件 {len(near_events)} 个",
    ]
    for ev, n in near_events.most_common(10):
        lines.append(f"  - {ev}: 出现 {n} 次")
    lines += [
        "",
        "## 解读注意事项",
        "",
        "- 扫描间隔为 2 小时,只能捕捉**持续存在**的错价;毫秒级消失的套利机会",
        "  本方法天然测不到,所以真实机会数是这里的上限还是下限无法断言——",
        "  但\"持续错价\"恰恰才是小资金手动可吃到的那类。",
        "- 理论利润未计入成交时对手撤单的风险(实际下单时报价可能已消失)。",
        "- 结论应基于:一周内可执行机会的**频率**与**单次利润量级**,",
        "  对比投入的时间成本,判断是否值得实盘。",
    ]
    out = os.path.join(os.path.dirname(data_dir), "REPORT.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    main(sys.argv[1] if len(sys.argv) > 1 else default_dir)
