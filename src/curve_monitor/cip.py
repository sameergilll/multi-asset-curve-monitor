from __future__ import annotations

from dataclasses import dataclass
import math

from .curves import ZeroCurve


@dataclass(frozen=True)
class CIPResult:
    tenor_years: float
    market_forward: float
    theoretical_forward: float
    deviation_pips: float
    implied_basis_bp: float
    signal: str


def theoretical_forward(
    spot: float, tenor_years: float, base_curve: ZeroCurve, quote_curve: ZeroCurve
) -> float:
    """CIP forward for quote units per one unit of base currency."""
    return spot * base_curve.discount(tenor_years) / quote_curve.discount(tenor_years)


def cip_deviation(
    spot: float,
    market_forward: float,
    tenor_years: float,
    base_curve: ZeroCurve,
    quote_curve: ZeroCurve,
    alert_threshold_bp: float = 5.0,
    pip_size: float = 1e-4,
) -> CIPResult:
    theo = theoretical_forward(spot, tenor_years, base_curve, quote_curve)
    deviation_pips = (market_forward - theo) / pip_size
    basis_bp = math.log(market_forward / theo) / tenor_years * 10_000.0
    if basis_bp > alert_threshold_bp:
        signal = "market forward rich vs CIP"
    elif basis_bp < -alert_threshold_bp:
        signal = "market forward cheap vs CIP"
    else:
        signal = "within threshold"
    return CIPResult(tenor_years, market_forward, theo, deviation_pips, basis_bp, signal)
