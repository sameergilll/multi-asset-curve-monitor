from __future__ import annotations

from collections.abc import Iterable
from .curves import ZeroCurve
from .risk import portfolio_pv


def parallel_scenario(instruments: Iterable, curve: ZeroCurve, shift_bp: float) -> dict[str, float]:
    instruments = list(instruments)
    base = portfolio_pv(instruments, curve)
    stressed = portfolio_pv(instruments, curve.shifted(shift_bp))
    return {"shift_bp": shift_bp, "base_pv": base, "stressed_pv": stressed, "pnl": stressed - base}


def steepener_scenario(instruments: Iterable, curve: ZeroCurve, short_bp: float = -10, long_bp: float = 10) -> dict[str, float]:
    instruments = list(instruments)
    base = portfolio_pv(instruments, curve)
    rates = curve.zero_rate(curve.times)
    t0, t1 = curve.times[0], curve.times[-1]
    weights = (curve.times - t0) / (t1 - t0)
    shifts = (short_bp + (long_bp - short_bp) * weights) / 10_000.0
    stressed = ZeroCurve(curve.times, __import__('numpy').exp(-(rates + shifts) * curve.times))
    pv = portfolio_pv(instruments, stressed)
    return {"short_bp": short_bp, "long_bp": long_bp, "base_pv": base, "stressed_pv": pv, "pnl": pv - base}
