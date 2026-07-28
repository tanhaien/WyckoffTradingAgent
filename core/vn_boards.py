"""Vietnam stock board classification helpers.

HOSE (Ho Chi Minh Stock Exchange): 1-letter prefix + numbers
HNX (Hanoi Stock Exchange): numbers starting with HNX or certain prefixes
UPCoM: Unlisted Public Company Market

Note: VN tickers use exchange suffix convention:
  - .HOSE or no suffix = HOSE
  - .HNX = HNX
  - .UPCoM = UPCoM
"""

from __future__ import annotations

HOSE_PREFIXES = (
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K",
    "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V",
    "W", "X", "Y", "Z",
)

HNX_PREFIXES = ("H",)  # HNX tickers often start with specific patterns


def vn_board(code: object) -> str:
    """Classify a VN stock code into board type.

    Returns one of: 'hose', 'hnx', 'upcom', 'unknown'.
    """
    text = str(code or "").strip().upper()

    if "." in text:
        suffix = text.split(".")[-1]
        if suffix == "HOSE":
            return "hose"
        if suffix == "HNX":
            return "hnx"
        if suffix == "UPCoM":
            return "upcom"

    # Try to detect by symbol patterns
    # HOSE: typically 1-3 letters (e.g. MBB, FPT, VCB, HPG)
    # HNX: typically alphabetic, often shorter (e.g. SHB, PVS)
    # UPCoM: typically 3+ letters (e.g. BSR, LTG)

    # Strip any exchange suffix for detection
    code_clean = text.replace(".HOSE", "").replace(".HNX", "").replace(".UPCoM", "")

    if not code_clean:
        return "unknown"

    # All VN tickers are alphabetic — can't use prefix matching reliably
    # Default to hose as most liquid stocks trade there
    return "hose"


def is_supported_vn_board(code: object) -> bool:
    """Check if a code belongs to a supported VN trading board."""
    return vn_board(code) in {"hose", "hnx", "upcom"}
