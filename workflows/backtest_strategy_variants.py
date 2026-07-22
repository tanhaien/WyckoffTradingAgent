"""Controlled classic and A-share empirical strategy ablation definitions."""

from __future__ import annotations

from core.a_share_entry_research import AShareEntryResearchPolicy

VARIANT_LABELS = {
    "live": "当前生产配置",
    "A": "基线",
    "B": "基线 + Upthrust/UTAD",
    "C": "基线 + regime 触发阈值分层",
    "D": "基线 + Creek/LPS + 跨信号时序加分",
    "E": "B+C+D 全部开启",
    "F": "A股实证：纯消融 EVR，不递补次级候选",
    "G": "A股实证：纯消融 EVR/SOS，不递补次级候选",
    "H": "A股实证：NEUTRAL 入场需广度确认",
    "J": "A股实证：Spring 强价格确认，不递补次级候选",
    "K": "A股实证：信号族按市场水温分层，不递补次级候选",
}

DEFAULT_COMPARISON_VARIANTS = ("A", "F", "G", "H", "J", "K")

_ALL_SWITCHES = {
    "dist_upthrust_enabled": False,
    "regime_trigger_profiles_enabled": False,
    "lps_creek_confirmation_enabled": False,
    "signal_sequence_bonus_enabled": False,
}

_VARIANT_SWITCHES = {
    "A": {},
    "B": {"dist_upthrust_enabled": True},
    "C": {"regime_trigger_profiles_enabled": True},
    "D": {"lps_creek_confirmation_enabled": True, "signal_sequence_bonus_enabled": True},
    "E": {
        "dist_upthrust_enabled": True,
        "regime_trigger_profiles_enabled": True,
        "lps_creek_confirmation_enabled": True,
        "signal_sequence_bonus_enabled": True,
    },
    "F": {},
    "G": {},
    "H": {},
    "J": {},
    "K": {},
}

_ENTRY_POLICIES = {
    "F": AShareEntryResearchPolicy(
        blocked_confirmed_signals=("evr",),
        preserve_rank_slots_before_filtering=True,
    ),
    "G": AShareEntryResearchPolicy(
        blocked_confirmed_signals=("evr", "sos"),
        preserve_rank_slots_before_filtering=True,
    ),
    "H": AShareEntryResearchPolicy(require_neutral_breadth_confirmation=True),
    "J": AShareEntryResearchPolicy(
        preserve_rank_slots_before_filtering=True,
        require_strong_spring_confirmation=True,
    ),
    "K": AShareEntryResearchPolicy(
        blocked_confirmed_signals_by_regime=(
            ("NEUTRAL", ("spring", "evr")),
            ("PANIC_REPAIR_CONFIRMED", ("spring", "sos")),
            ("PANIC_REPAIR_INTRADAY", ("spring", "sos")),
        ),
        preserve_rank_slots_before_filtering=True,
    ),
}


def normalize_strategy_variant(raw: str) -> str:
    value = str(raw or "live").strip()
    normalized = value.upper() if value.lower() != "live" else "live"
    if normalized not in VARIANT_LABELS:
        raise ValueError("strategy_variant 必须是 live / A / B / C / D / E / F / G / H / J / K")
    return normalized


def strategy_variant_overrides(raw: str) -> dict[str, object]:
    variant = normalize_strategy_variant(raw)
    if variant == "live":
        return {}
    return {**_ALL_SWITCHES, **_VARIANT_SWITCHES[variant]}


def strategy_variant_label(raw: str) -> str:
    return VARIANT_LABELS[normalize_strategy_variant(raw)]


def strategy_variant_entry_policy(raw: str) -> AShareEntryResearchPolicy:
    return _ENTRY_POLICIES.get(normalize_strategy_variant(raw), AShareEntryResearchPolicy())
