"""Research-only A-share entry policies derived from realized signal outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AShareEntryResearchPolicy:
    blocked_confirmed_signals: tuple[str, ...] = ()
    blocked_confirmed_signals_by_regime: tuple[tuple[str, tuple[str, ...]], ...] = ()
    preserve_rank_slots_before_filtering: bool = False
    require_neutral_breadth_confirmation: bool = False
    require_strong_spring_confirmation: bool = False
    neutral_breadth_ratio_min: float = 50.0
    neutral_breadth_delta_min: float = 0.0
    neutral_daily_up_ratio_min: float = 50.0
    neutral_breadth_sample_min: int = 100
    spring_reclaim_pct_min: float = 1.0
    spring_close_position_min: float = 65.0


def normalized_signal_type(raw: object) -> str:
    return str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")


def confirmed_signal_allowed(
    policy: AShareEntryResearchPolicy,
    signal_type: object,
    *,
    regime: object = "",
) -> bool:
    signal = normalized_signal_type(signal_type)
    blocked = {normalized_signal_type(item) for item in policy.blocked_confirmed_signals}
    if signal in blocked:
        return False
    regime_key = str(regime or "").strip().upper()
    for configured_regime, configured_signals in policy.blocked_confirmed_signals_by_regime:
        if regime_key == str(configured_regime).strip().upper():
            return signal not in {normalized_signal_type(item) for item in configured_signals}
    return True


def market_context_allows_entry(
    policy: AShareEntryResearchPolicy,
    *,
    regime: object,
    breadth: dict[str, Any] | None,
) -> bool:
    if not policy.require_neutral_breadth_confirmation:
        return True
    if str(regime or "").strip().upper() != "NEUTRAL":
        return True
    data = breadth or {}
    return (
        _number(data.get("ratio_pct")) >= policy.neutral_breadth_ratio_min
        and _number(data.get("delta_pct")) >= policy.neutral_breadth_delta_min
        and _number(data.get("daily_up_ratio_pct")) >= policy.neutral_daily_up_ratio_min
        and int(data.get("sample_size") or 0) >= policy.neutral_breadth_sample_min
    )


def confirmed_item_allowed(
    policy: AShareEntryResearchPolicy,
    item: dict[str, Any],
    *,
    regime: object,
    history: pd.DataFrame | None,
) -> bool:
    signal_type = item.get("signal_type")
    if not confirmed_signal_allowed(policy, signal_type, regime=regime):
        return False
    if not policy.require_strong_spring_confirmation or normalized_signal_type(signal_type) != "spring":
        return True
    return _strong_spring_confirmation(policy, item, history)


def _strong_spring_confirmation(
    policy: AShareEntryResearchPolicy,
    item: dict[str, Any],
    history: pd.DataFrame | None,
) -> bool:
    required = {"date", "open", "high", "low", "close"}
    if history is None or history.empty or not required.issubset(history.columns):
        return False
    frame = history.sort_values("date")
    close = pd.to_numeric(frame["close"], errors="coerce")
    latest = frame.iloc[-1]
    signal_dates = pd.to_datetime(frame["date"], errors="coerce").dt.date
    signal_date = pd.to_datetime(item.get("signal_date"), errors="coerce")
    matches = close[signal_dates == signal_date.date()] if not pd.isna(signal_date) else pd.Series(dtype=float)
    ma20 = close.rolling(20).mean().iloc[-1]
    values = pd.to_numeric(latest[["open", "high", "low", "close"]], errors="coerce")
    if matches.empty or pd.isna(ma20) or values.isna().any() or values["high"] <= values["low"]:
        return False
    close_position = (values["close"] - values["low"]) / (values["high"] - values["low"]) * 100.0
    reclaim = float(matches.iloc[-1]) * (1.0 + policy.spring_reclaim_pct_min / 100.0)
    return bool(
        values["close"] >= max(float(ma20), reclaim)
        and values["close"] > values["open"]
        and close_position >= policy.spring_close_position_min
    )


def _number(raw: object) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float("-inf")
    return value if value == value else float("-inf")
