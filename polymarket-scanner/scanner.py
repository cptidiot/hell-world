#!/usr/bin/env python3
"""Polymarket structural-arbitrage scanner.

Scans public Polymarket APIs (no auth, read-only) for structural mispricings:

  1. Negative-risk arb across a mutually-exclusive multi-outcome event:
     buying 1 share of YES in every outcome costs sum(YES asks); exactly one
     outcome pays $1, so sum < $1 is risk-free profit (before slippage).
     Symmetrically, buying every NO costs sum(NO asks) and pays $(N-1).
  2. Crossed single binary market: YES ask + NO ask < $1.

For each candidate found via Gamma API prices, the full CLOB order books are
fetched and a depth-aware fill is simulated against a paper bankroll, so the
logged profit is what was actually executable at that instant, not just the
top-of-book fantasy number.

Outputs (append-only JSONL under --data-dir):
  scans.jsonl          one line per scan: coverage, best sums seen, status
  opportunities.jsonl  one line per executable opportunity, with simulated fill
  near_misses.jsonl    events whose best sum came within NEAR_MISS of parity

Usage:
  python3 scanner.py                 # one live scan
  python3 scanner.py --selftest      # validate detection math on fixtures
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

BANKROLL_USD = 2000.0        # paper-trading capital cap per opportunity
MIN_EDGE = 0.005             # ignore "arbs" thinner than 0.5c per $1 payout
NEAR_MISS = 0.02             # log events within 2c of parity for the report
MAX_EVENTS = 3000            # pagination cap on Gamma events per scan
BOOK_DELAY_S = 0.15          # politeness delay between order-book requests
HTTP_TIMEOUT = 20


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get_json(url, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pm-scan/1.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last_err}")


def fetch_active_events():
    events, offset, page = [], 0, 100
    while offset < MAX_EVENTS:
        url = f"{GAMMA}/events?" + urllib.parse.urlencode(
            {"active": "true", "closed": "false", "limit": page, "offset": offset}
        )
        batch = http_get_json(url)
        if not batch:
            break
        events.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return events


def parse_json_field(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    return v


def market_quotes(market):
    """Best YES ask and NO ask implied by Gamma fields; None when unquoted."""
    ask = market.get("bestAsk")
    bid = market.get("bestBid")
    if ask is None or bid is None:
        return None
    ask, bid = float(ask), float(bid)
    if not (0.0 < ask <= 1.0 and 0.0 <= bid < 1.0):
        return None
    return {"yes_ask": ask, "no_ask": round(1.0 - bid, 6)}


# ---------------------------------------------------------------------------
# Depth-aware fill simulation
# ---------------------------------------------------------------------------

def cost_to_buy(asks, shares):
    """Cost of buying `shares` walking the ask levels; None if depth short."""
    remaining, cost = shares, 0.0
    for level in asks:
        px, sz = float(level["price"]), float(level["size"])
        take = min(sz, remaining)
        cost += take * px
        remaining -= take
        if remaining <= 1e-9:
            return cost
    return None


def max_shares_available(asks_per_leg):
    return min(sum(float(l["size"]) for l in asks) if asks else 0.0
               for asks in asks_per_leg)


def simulate_basket(asks_per_leg, payout_per_share, bankroll=BANKROLL_USD):
    """Best executable profit buying an equal number of shares on every leg.

    Scans candidate sizes up to depth/bankroll and returns the size with max
    total profit (profit per share shrinks as fills walk the book).
    """
    depth_cap = max_shares_available(asks_per_leg)
    if depth_cap < 1:
        return None
    best = None
    n_steps = 40
    for i in range(1, n_steps + 1):
        shares = depth_cap * i / n_steps
        costs = [cost_to_buy(asks, shares) for asks in asks_per_leg]
        if any(c is None for c in costs):
            break
        total_cost = sum(costs)
        if total_cost > bankroll:
            # shrink to bankroll proportionally and stop growing
            shares *= bankroll / total_cost
            costs = [cost_to_buy(asks, shares) for asks in asks_per_leg]
            if any(c is None for c in costs):
                break
            total_cost = sum(costs)
        profit = shares * payout_per_share - total_cost
        if best is None or profit > best["profit_usd"]:
            best = {
                "shares": round(shares, 2),
                "cost_usd": round(total_cost, 2),
                "payout_usd": round(shares * payout_per_share, 2),
                "profit_usd": round(profit, 2),
            }
        if total_cost >= bankroll:
            break
    if best and best["profit_usd"] > 0:
        best["return_pct"] = round(100 * best["profit_usd"] / best["cost_usd"], 3)
        return best
    return None


def fetch_book_asks(token_id):
    book = http_get_json(f"{CLOB}/book?token_id={urllib.parse.quote(token_id)}")
    asks = book.get("asks") or []
    # CLOB returns asks sorted worst-first; sort best (lowest) first
    return sorted(asks, key=lambda l: float(l["price"]))


# ---------------------------------------------------------------------------
# Candidate detection from Gamma snapshot
# ---------------------------------------------------------------------------

def find_candidates(events):
    """Return (candidates, near_misses, stats) using Gamma top-of-book prices."""
    candidates, near_misses = [], []
    n_markets = 0
    best_yes_sum = None
    for ev in events:
        markets = ev.get("markets") or []
        quoted = []
        for m in markets:
            if m.get("closed") or not m.get("active"):
                continue
            q = market_quotes(m)
            tokens = parse_json_field(m.get("clobTokenIds"))
            if q and tokens and len(tokens) == 2:
                quoted.append((m, q, tokens))
        n_markets += len(quoted)

        # 1. crossed single binary market
        for m, q, tokens in quoted:
            s = q["yes_ask"] + q["no_ask"]
            if s < 1.0 - MIN_EDGE:
                candidates.append({
                    "kind": "binary_cross",
                    "event": ev.get("title"),
                    "market": m.get("question"),
                    "slug": ev.get("slug"),
                    "gamma_sum": round(s, 4),
                    "legs": [tokens[0], tokens[1]],
                    "payout_per_share": 1.0,
                })

        # 2. negative-risk basket across mutually-exclusive outcomes
        if ev.get("negRisk") and len(quoted) >= 2:
            yes_sum = sum(q["yes_ask"] for _, q, _ in quoted)
            no_sum = sum(q["no_ask"] for _, q, _ in quoted)
            n = len(quoted)
            if best_yes_sum is None or yes_sum < best_yes_sum[0]:
                best_yes_sum = (round(yes_sum, 4), ev.get("title"), n)
            if yes_sum < 1.0 - MIN_EDGE:
                candidates.append({
                    "kind": "negrisk_yes",
                    "event": ev.get("title"),
                    "slug": ev.get("slug"),
                    "n_outcomes": n,
                    "gamma_sum": round(yes_sum, 4),
                    "legs": [t[0] for _, _, t in quoted],
                    "payout_per_share": 1.0,
                })
            elif yes_sum <= 1.0 + NEAR_MISS + 1e-9:
                near_misses.append({
                    "kind": "negrisk_yes", "event": ev.get("title"),
                    "slug": ev.get("slug"), "n_outcomes": n,
                    "gamma_sum": round(yes_sum, 4),
                })
            if no_sum < (n - 1) - MIN_EDGE * n:
                candidates.append({
                    "kind": "negrisk_no",
                    "event": ev.get("title"),
                    "slug": ev.get("slug"),
                    "n_outcomes": n,
                    "gamma_sum": round(no_sum, 4),
                    "legs": [t[1] for _, _, t in quoted],
                    "payout_per_share": float(n - 1),
                })
    stats = {"n_markets_quoted": n_markets, "best_negrisk_yes_sum": best_yes_sum}
    return candidates, near_misses, stats


def verify_candidate(cand):
    """Re-check a Gamma candidate against live CLOB books; simulate the fill."""
    asks_per_leg = []
    for token in cand["legs"]:
        asks_per_leg.append(fetch_book_asks(token))
        time.sleep(BOOK_DELAY_S)
    fill = simulate_basket(asks_per_leg, cand["payout_per_share"])
    return fill


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def append_jsonl(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_scan(data_dir):
    t0 = time.time()
    ts = now_iso()
    scan_row = {"ts": ts, "status": "ok"}
    try:
        events = fetch_active_events()
    except RuntimeError as e:
        scan_row.update(status="network_error", error=str(e)[:300])
        append_jsonl(os.path.join(data_dir, "scans.jsonl"), scan_row)
        print(f"[{ts}] scan failed: {e}", file=sys.stderr)
        return 1

    candidates, near_misses, stats = find_candidates(events)
    executable = []
    for cand in candidates[:20]:  # book-check at most 20 candidates per scan
        try:
            fill = verify_candidate(cand)
        except RuntimeError as e:
            cand["verify_error"] = str(e)[:200]
            fill = None
        if fill:
            row = {"ts": ts, **cand, "fill": fill}
            executable.append(row)
            append_jsonl(os.path.join(data_dir, "opportunities.jsonl"), row)

    for nm in near_misses:
        append_jsonl(os.path.join(data_dir, "near_misses.jsonl"), {"ts": ts, **nm})

    scan_row.update(
        n_events=len(events),
        n_markets_quoted=stats["n_markets_quoted"],
        n_candidates_gamma=len(candidates),
        n_executable=len(executable),
        paper_profit_usd=round(sum(r["fill"]["profit_usd"] for r in executable), 2),
        n_near_misses=len(near_misses),
        best_negrisk_yes_sum=stats["best_negrisk_yes_sum"],
        duration_s=round(time.time() - t0, 1),
    )
    append_jsonl(os.path.join(data_dir, "scans.jsonl"), scan_row)
    print(json.dumps(scan_row, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Self-test on synthetic books (no network)
# ---------------------------------------------------------------------------

def selftest():
    failures = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name} {detail}")
        if not cond:
            failures.append(name)

    # 3-outcome neg-risk: asks sum to 0.97 at top of book -> ~3c/share edge
    legs = [
        [{"price": "0.40", "size": "500"}, {"price": "0.45", "size": "1000"}],
        [{"price": "0.35", "size": "300"}, {"price": "0.40", "size": "1000"}],
        [{"price": "0.22", "size": "800"}, {"price": "0.30", "size": "1000"}],
    ]
    fill = simulate_basket(legs, 1.0)
    check("negrisk detects profit", fill is not None and fill["profit_usd"] > 0,
          json.dumps(fill))
    check("respects bankroll", fill["cost_usd"] <= BANKROLL_USD + 0.01)
    # optimal here: 300 shares @ 0.97 = $291 cost, $9 profit; beyond 300 the
    # second leg walks to 0.40 making the sum 1.02 (a loss per marginal share)
    check("stops before book turns unprofitable",
          abs(fill["shares"] - 300) / 300 < 0.15, f"shares={fill['shares']}")

    # parity book: sum = 1.00 exactly -> no opportunity
    legs_par = [
        [{"price": "0.60", "size": "1000"}],
        [{"price": "0.40", "size": "1000"}],
    ]
    check("no false positive at parity", simulate_basket(legs_par, 1.0) is None)

    # crossed binary: yes 0.55 + no 0.42 = 0.97, deep books, bankroll binds
    legs_bin = [
        [{"price": "0.55", "size": "100000"}],
        [{"price": "0.42", "size": "100000"}],
    ]
    fill = simulate_basket(legs_bin, 1.0)
    check("bankroll caps deep-book fill", fill["cost_usd"] <= BANKROLL_USD + 0.01,
          json.dumps(fill))
    expected = BANKROLL_USD / 0.97 * 0.03
    check("profit math correct at cap",
          abs(fill["profit_usd"] - expected) < 1.0,
          f"got {fill['profit_usd']}, expected ~{expected:.2f}")

    # NO-side basket: 3 outcomes, NO asks sum 1.94, payout N-1=2 -> 6c/basket
    legs_no = [
        [{"price": "0.70", "size": "400"}],
        [{"price": "0.64", "size": "400"}],
        [{"price": "0.60", "size": "400"}],
    ]
    fill = simulate_basket(legs_no, 2.0)
    check("NO-side basket detects profit", fill is not None and fill["profit_usd"] > 0,
          json.dumps(fill))

    # gamma-side detection wiring
    ev = {
        "title": "Test event", "slug": "test", "negRisk": True,
        "markets": [
            {"active": True, "closed": False, "question": "A",
             "bestAsk": 0.40, "bestBid": 0.38, "clobTokenIds": '["a-yes","a-no"]'},
            {"active": True, "closed": False, "question": "B",
             "bestAsk": 0.35, "bestBid": 0.33, "clobTokenIds": '["b-yes","b-no"]'},
            {"active": True, "closed": False, "question": "C",
             "bestAsk": 0.22, "bestBid": 0.20, "clobTokenIds": '["c-yes","c-no"]'},
        ],
    }
    cands, _, _ = find_candidates([ev])
    check("find_candidates flags negrisk_yes sum 0.97",
          any(c["kind"] == "negrisk_yes" and abs(c["gamma_sum"] - 0.97) < 1e-6
              for c in cands))

    ev_fair = json.loads(json.dumps(ev))
    ev_fair["markets"][0]["bestAsk"] = 0.45  # sum 1.02 -> near-miss only
    cands, nms, _ = find_candidates([ev_fair])
    check("fair pricing yields no candidate", not cands)
    check("near-miss recorded", len(nms) == 1)

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    sys.exit(selftest() if args.selftest else run_scan(args.data_dir))
