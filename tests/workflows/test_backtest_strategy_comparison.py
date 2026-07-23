from pathlib import Path

from workflows.backtest_strategy_comparison import (
    build_strategy_comparison,
    load_strategy_comparison_rows,
    render_strategy_comparison,
)
from workflows.backtest_strategy_variants import DEFAULT_COMPARISON_VARIANTS


def _write_summary(
    root: Path, period: str, variant: str, cash_return: float, drawdown: float, *, run_number: int | None = None
) -> None:
    suffix = f"-{run_number}" if run_number is not None else ""
    target = root / f"backtest-strategy-{period}-{variant}{suffix}"
    target.mkdir(parents=True)
    (target / "summary_fixture.md").write_text(
        "\n".join(
            [
                "# Wyckoff Funnel Daily Backtest",
                "- 区间: 2020-01-01 ~ 2020-06-30",
                "- 策略消融组: " + variant,
                "- 平均收益: 1.25%",
                "- 夏普比 (Sharpe Ratio): 1.5",
                "- 成交样本: 30",
                "## 真实现金账户模拟",
                f"- 总收益: {cash_return}%",
                f"- 现金最大回撤: {drawdown}%",
                "- 成交笔数: 24",
                "- 胜率: 55%",
            ]
        ),
        encoding="utf-8",
    )
    (target / "trades_fixture.csv").write_text(
        f"signal_date,code\n2020-01-02,{period}-{variant}\n",
        encoding="utf-8",
    )


def test_strategy_comparison_builds_relative_and_walk_forward_results(tmp_path: Path) -> None:
    periods = ["bull_2020", "bear_2022", "recent_6m", "recent_2m"]
    for period_index, period in enumerate(periods):
        for variant_index, variant in enumerate(DEFAULT_COMPARISON_VARIANTS):
            _write_summary(tmp_path, period, variant, 2.0 + variant_index + period_index, -4.0)

    rows = load_strategy_comparison_rows(tmp_path)
    report = build_strategy_comparison(rows)

    assert len(rows) == 24
    assert report["status"] == "ready"
    assert report["evaluations"]["M"]["reference_variant"] == "A"
    assert report["evaluations"]["O"]["reference_variant"] == "M"
    assert report["evaluations"]["R"]["status"] == "pass"
    assert report["evaluations"]["R"]["exposure_periods"] == 4
    assert report["evaluations"]["R"]["changed_trades"] == 8
    assert len(report["walk_forward"]["windows"]) == 2
    assert "相对参照组结论" in render_strategy_comparison(report)


def test_strategy_comparison_requires_all_default_period_cells(tmp_path: Path) -> None:
    for period in ("bull_2020", "bear_2022", "recent_6m"):
        for variant in DEFAULT_COMPARISON_VARIANTS:
            _write_summary(tmp_path, period, variant, 2.0, -4.0)

    report = build_strategy_comparison(load_strategy_comparison_rows(tmp_path))

    assert report["status"] == "incomplete"
    assert set(report["missing_cells"]) == {
        "recent_2m/A",
        "recent_2m/M",
        "recent_2m/O",
        "recent_2m/P",
        "recent_2m/Q",
        "recent_2m/R",
    }


def test_strategy_comparison_uses_executed_cash_trade_average(tmp_path: Path) -> None:
    _write_summary(tmp_path, "recent_6m", "A", 2.0, -4.0)
    target = tmp_path / "backtest-strategy-recent_6m-A" / "cash_trades_fixture.csv"
    target.write_text("ret_pct\n-5\n3\n", encoding="utf-8")

    row = load_strategy_comparison_rows(tmp_path)[0]

    assert row.avg_return == -1.0


def test_strategy_comparison_accepts_github_artifact_run_suffix(tmp_path: Path) -> None:
    _write_summary(tmp_path, "recent_6m", "A", 2.0, -4.0, run_number=72)

    rows = load_strategy_comparison_rows(tmp_path)

    assert [(row.period, row.variant) for row in rows] == [("recent_6m", "A")]


def test_strategy_comparison_marks_identical_trade_sets_as_no_effect(tmp_path: Path) -> None:
    for period in ("bull_2020", "bear_2022", "recent_6m"):
        _write_summary(tmp_path, period, "A", 2.0, -4.0)
        _write_summary(tmp_path, period, "B", 3.0, -4.0)
        for variant in ("A", "B"):
            target = tmp_path / f"backtest-strategy-{period}-{variant}" / "trades_fixture.csv"
            target.write_text("signal_date,code\n2020-01-02,SAME\n", encoding="utf-8")

    report = build_strategy_comparison(load_strategy_comparison_rows(tmp_path))

    assert report["evaluations"]["B"]["status"] == "no_effect"
    assert report["evaluations"]["B"]["changed_trades"] == 0


def test_strategy_comparison_counts_position_weight_as_treatment_exposure(tmp_path: Path) -> None:
    for period in ("bull_2020", "bear_2022", "recent_6m"):
        _write_summary(tmp_path, period, "A", 2.0, -4.0)
        _write_summary(tmp_path, period, "M", 3.0, -4.0)
        baseline = tmp_path / f"backtest-strategy-{period}-A" / "trades_fixture.csv"
        candidate = tmp_path / f"backtest-strategy-{period}-M" / "trades_fixture.csv"
        baseline.write_text(
            "signal_date,code,entry_weight_multiplier\n2020-01-02,SAME,1.0\n",
            encoding="utf-8",
        )
        candidate.write_text(
            "signal_date,code,entry_weight_multiplier\n2020-01-02,SAME,0.5\n",
            encoding="utf-8",
        )

    report = build_strategy_comparison(load_strategy_comparison_rows(tmp_path))

    assert report["evaluations"]["M"]["exposure_periods"] == 3
    assert report["evaluations"]["M"]["changed_trades"] == 6


def test_strategy_comparison_counts_changed_exit_as_treatment_exposure(tmp_path: Path) -> None:
    for period in ("bull_2020", "bear_2022", "recent_6m"):
        _write_summary(tmp_path, period, "M", 2.0, -4.0)
        _write_summary(tmp_path, period, "P", 3.0, -4.0)
        baseline = tmp_path / f"backtest-strategy-{period}-M" / "trades_fixture.csv"
        candidate = tmp_path / f"backtest-strategy-{period}-P" / "trades_fixture.csv"
        baseline.write_text(
            "signal_date,code,entry_weight_multiplier,exit_date\n2020-01-02,SAME,1.0,2020-01-20\n",
            encoding="utf-8",
        )
        candidate.write_text(
            "signal_date,code,entry_weight_multiplier,exit_date\n2020-01-02,SAME,1.0,2020-01-15\n",
            encoding="utf-8",
        )

    report = build_strategy_comparison(load_strategy_comparison_rows(tmp_path))

    assert report["evaluations"]["P"]["exposure_periods"] == 3
    assert report["evaluations"]["P"]["changed_trades"] == 6
