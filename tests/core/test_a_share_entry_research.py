import pandas as pd

from core.a_share_entry_research import (
    AShareEntryResearchPolicy,
    confirmed_item_allowed,
    confirmed_signal_allowed,
    entry_weight_multiplier,
    market_context_allows_entry,
    rank_confirmed_items,
)


def test_blocked_confirmed_signal_is_not_tradeable() -> None:
    policy = AShareEntryResearchPolicy(blocked_confirmed_signals=("evr", "sos"))

    assert not confirmed_signal_allowed(policy, "EVR")
    assert not confirmed_signal_allowed(policy, "sos")
    assert confirmed_signal_allowed(policy, "spring")


def test_regime_signal_policy_only_blocks_configured_market_state() -> None:
    policy = AShareEntryResearchPolicy(blocked_confirmed_signals_by_regime=(("NEUTRAL", ("spring", "evr")),))

    assert not confirmed_signal_allowed(policy, "spring", regime="NEUTRAL")
    assert confirmed_signal_allowed(policy, "sos", regime="NEUTRAL")
    assert confirmed_signal_allowed(policy, "spring", regime="CAUTION")


def test_neutral_breadth_gate_fails_closed_but_does_not_replace_other_regimes() -> None:
    policy = AShareEntryResearchPolicy(require_neutral_breadth_confirmation=True)
    strong = {"ratio_pct": 55, "delta_pct": 2, "daily_up_ratio_pct": 60, "sample_size": 1000}

    assert market_context_allows_entry(policy, regime="NEUTRAL", breadth=strong)
    assert not market_context_allows_entry(policy, regime="NEUTRAL", breadth={})
    assert market_context_allows_entry(policy, regime="CAUTION", breadth={})


def test_strong_spring_confirmation_requires_price_reclaim_and_strong_close() -> None:
    dates = pd.date_range("2026-01-01", periods=21)
    history = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 21,
            "high": [10.1] * 20 + [10.25],
            "low": [9.9] * 20 + [9.95],
            "close": [10.0] * 20 + [10.2],
        }
    )
    policy = AShareEntryResearchPolicy(require_strong_spring_confirmation=True)
    item = {"signal_type": "spring", "signal_date": dates[-2].date().isoformat()}

    assert confirmed_item_allowed(policy, item, regime="NEUTRAL", history=history)

    history.loc[history.index[-1], "close"] = 10.05
    assert not confirmed_item_allowed(policy, item, regime="NEUTRAL", history=history)
    assert confirmed_item_allowed(policy, {"signal_type": "sos"}, regime="NEUTRAL", history=None)


def test_balanced_rank_interleaves_signal_families_without_losing_family_score_order() -> None:
    items = [
        {"code": "S1", "score": 100, "signal_type": "spring"},
        {"code": "S2", "score": 90, "signal_type": "spring"},
        {"code": "E1", "score": 8, "signal_type": "evr"},
        {"code": "O1", "score": 4, "signal_type": "sos"},
    ]
    policy = AShareEntryResearchPolicy(balance_confirmed_signal_families=True)

    ranked = rank_confirmed_items(items, policy)
    rotated = rank_confirmed_items(items, policy, rotation_key=1)

    assert [item["code"] for item in ranked] == ["O1", "E1", "S1", "S2"]
    assert [item["code"] for item in rotated] == ["E1", "S1", "O1", "S2"]


def test_entry_weight_multiplier_matches_regime_and_signal_and_clamps_value() -> None:
    policy = AShareEntryResearchPolicy(
        entry_weight_multipliers=(
            ("NEUTRAL", "spring", 0.5),
            ("CAUTION", "sos", 2.0),
        )
    )

    assert entry_weight_multiplier(policy, "SPRING", "neutral") == 0.5
    assert entry_weight_multiplier(policy, "sos", "CAUTION") == 1.0
    assert entry_weight_multiplier(policy, "evr", "NEUTRAL") == 1.0
