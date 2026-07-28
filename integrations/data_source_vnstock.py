"""Vnstock (Vietnam stock) history provider — vnstock 4.x."""

from __future__ import annotations

import os
import time

import pandas as pd

from integrations.data_source_format import compact_error as _compact_error

_RETRY_TIMES = max(int(os.getenv("VNSTOCK_RETRY_TIMES", "2")), 1)
_RETRY_SLEEP_SECONDS = float(os.getenv("VNSTOCK_RETRY_SLEEP_SECONDS", "0.5"))


def fetch_stock_vnstock(symbol: str, start: str, end: str, adjust: str = "") -> pd.DataFrame | None:
    """Fetch Vietnam stock history via vnstock.

    Parameters
    ----------
    symbol : str
        VN ticker (e.g. "MBB", "FPT", "HPG").
    start : str
        Start date in YYYYMMDD format.
    end : str
        End date in YYYYMMDD format.
    adjust : str
            Ignored for VN stocks (no forward/back adjustment concept in vnstock).

    Returns
    -------
    pd.DataFrame
        DataFrame with Chinese column names matching upstream convention:
        日期, 开盘, 最高, 最低, 收盘, 成交量, 成交额, 涨跌幅, 换手率, 振幅
    """
    for attempt in range(1, _RETRY_TIMES + 1):
        try:
            return _fetch_vnstock_once(symbol, start, end)
        except ModuleNotFoundError:
            raise
        except Exception as exc:
            if attempt < _RETRY_TIMES and _is_retryable_error(exc):
                time.sleep(max(_RETRY_SLEEP_SECONDS, 0.0))
                continue
            raise
    raise RuntimeError(f"vnstock retry exhausted for {symbol}")


def _fetch_vnstock_once(symbol: str, start: str, end: str) -> pd.DataFrame:
    from vnstock.api.quote import Quote

    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    q = Quote(symbol=symbol, source="VCI")
    raw = q.history(start=start_fmt, end=end_fmt)

    if raw is None or raw.empty:
        raise RuntimeError(f"vnstock empty for {symbol}")

    df = raw.copy()
    df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d")

    # Compute missing columns
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    # 涨跌幅: pct change from previous close
    df["pct_chg"] = close.pct_change() * 100

    # 成交额: approximated as close * volume (VND)
    df["amount"] = close * volume

    # 换手率: not computable without shares outstanding; leave NA
    df["turnover"] = pd.NA

    # 振幅: (high - low) / prev_close * 100
    prev_close = close.shift(1)
    df["amplitude"] = (df["high"].astype(float) - df["low"].astype(float)) / prev_close * 100

    # Rename to Chinese column names (upstream convention)
    col_map = {
        "time": "日期",
        "open": "开盘",
        "high": "最高",
        "low": "最低",
        "close": "收盘",
        "volume": "成交量",
        "amount": "成交额",
        "pct_chg": "涨跌幅",
        "turnover": "换手率",
        "amplitude": "振幅",
    }
    df = df.rename(columns=col_map)
    df = df[[c for c in col_map.values() if c in df.columns]].copy()

    # Convert to numeric
    for col in df.columns:
        if col != "日期":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.attrs["source"] = "vnstock"
    return df


def _is_retryable_error(err: Exception) -> bool:
    text = _compact_error(err).lower()
    markers = [
        "remotedisconnected",
        "connection aborted",
        "connection reset",
        "read timed out",
        "connecttimeout",
        "timeout",
    ]
    return any(m in text for m in markers)
