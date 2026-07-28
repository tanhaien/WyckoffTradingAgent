#!/usr/bin/env python3
"""Wyckoff VN Stock Scanner — quick Wyckoff analysis for Vietnam stocks.

Usage:
    python3 scripts/vn_wyckoff_scan.py MBB FPT HPG
    python3 scripts/vn_wyckoff_scan.py --all  (scan all VN stocks)
    python3 scripts/vn_wyckoff_scan.py MBB   (detailed report)
"""

from __future__ import annotations

import logging
import sys
import warnings
from datetime import date, timedelta

import pandas as pd

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# Project imports
sys.path.insert(0, ".")

from integrations.data_source import fetch_stock_hist  # noqa: E402
from core.wyckoff_engine import (  # noqa: E402
    FunnelConfig,
    normalize_hist_from_fetch,
    analyze_accum_stage,
    detect_accum_stage,
    layer4_triggers,
)
from core.wyckoff_structure import (  # noqa: E402
    identify_trading_range,
    detect_structure_triggers,
)

# ── VN-specific FunnelConfig ──────────────────────────────────────────────


def vn_funnel_config() -> FunnelConfig:
    """Return a FunnelConfig tuned for Vietnam market scale."""
    cfg = FunnelConfig()
    # VN stocks: prices in thousands VND (e.g. MBB=22.0), market cap in trillions
    cfg.trading_days = 320
    # Lower close price floor for VND-denominated stocks
    cfg.l1_min_close_price = 2.0  # 2,000 VND minimum (very cheap stocks)
    # Market cap in 亿 unit (1亿 = 100M VND = 0.1B VND)
    # For context: typical VN listed stock cap is 500-500,000亿 VND
    cfg.min_market_cap_yi = 100.0  # 100亿 VND = 10B VND ≈ $400K USD
    # Amount floor (in 万 unit; 1万 = 10K)
    cfg.min_avg_amount_wan = 2000.0  # 2000万 VND = 20B VND daily avg
    return cfg


# ── Analysis ─────────────────────────────────────────────────────────────


def analyze_vn_stock(symbol: str, days: int = 320) -> dict:
    """Run Wyckoff analysis on a single VN stock."""
    end = date.today()
    start = end - timedelta(days=days * 2)  # buffer for non-trading days

    try:
        raw = fetch_stock_hist(symbol, start.isoformat(), end.isoformat())
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "ok": False}

    if raw is None or raw.empty:
        return {"symbol": symbol, "error": "no data", "ok": False}

    df = normalize_hist_from_fetch(raw)
    cfg = vn_funnel_config()

    result = {
        "symbol": symbol,
        "ok": True,
        "rows": len(df),
        "last_close": float(df["close"].iloc[-1]),
        "last_date": str(df["date"].iloc[-1]),
    }

    # Accumulation stage
    try:
        accum = analyze_accum_stage(df, cfg)
        result["accum_stage"] = str(accum or "none")
    except Exception as e:
        result["accum_stage"] = f"error: {e}"

    # Accum detailed
    try:
        det = detect_accum_stage([symbol], {symbol: df}, cfg)
        result["accum_detailed"] = str(det.get(symbol, "none"))
    except Exception as e:
        result["accum_detailed"] = f"error: {e}"

    # L4 Wyckoff triggers
    try:
        trigs = layer4_triggers([symbol], {symbol: df}, cfg)
        # extract just signal names
        if isinstance(trigs, dict):
            active = {k: v for k, v in trigs.items() if v}
            result["triggers"] = active
        else:
            result["triggers"] = {}
    except Exception as e:
        result["triggers"] = f"error: {e}"

    return result


# ── Report ───────────────────────────────────────────────────────────────


def print_report(results: list[dict]) -> None:
    """Print formatted analysis report."""
    print(f"\n{'═'*60}")
    print(f"  WYCKOFF VN STOCK SCAN — {date.today()}")
    print(f"{'═'*60}\n")

    ok = [r for r in results if r.get("ok")]
    fail = [r for r in results if not r.get("ok")]

    for r in ok:
        print(f"  📊 {r['symbol']:5s} | {r['last_close']:8.2f} | {r['last_date']}")
        stage = r.get("accum_stage", "?")
        detail = r.get("accum_detailed", "")
        trigs = r.get("triggers", {})
        trig_str = ", ".join(trigs.keys()) if isinstance(trigs, dict) and trigs else "none"

        print(f"       Accum: {stage}")
        print(f"       Detail: {detail[:80]}")
        print(f"       Signals: {trig_str}")
        print()

    for r in fail:
        print(f"  ❌ {r['symbol']:5s} | ERROR: {r.get('error', '?')}")

    print(f"\n  {'─'*50}")
    print(f"  Total: {len(results)} | OK: {len(ok)} | Fail: {len(fail)}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["MBB", "FPT", "HPG", "VNM", "TCB", "MSB"]

    if symbols == ["--all"]:
        # Scan all VN stocks — heavy operation
        from integrations.market_universe import load_vn_symbols

        syms, _ = load_vn_symbols()
        symbols = syms[:50]  # limit to first 50 for safety
        print(f"Scanning {len(symbols)} VN stocks...")

    results = []
    for sym in symbols:
        r = analyze_vn_stock(sym)
        results.append(r)
        if r.get("ok"):
            print(f"  ✓ {sym:5s} | {r['last_close']:>8.2f} | accum={r.get('accum_stage','?'):10s} | triggers={r.get('triggers','?')}")
        else:
            print(f"  ✗ {sym:5s} | {r.get('error','?')}")

    print_report(results)


if __name__ == "__main__":
    main()
