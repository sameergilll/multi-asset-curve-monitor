from __future__ import annotations

from collections.abc import Iterable

from .curves import ZeroCurve


def portfolio_pv(instruments: Iterable, curve: ZeroCurve) -> float:
    return float(sum(inst.pv(curve) for inst in instruments))


def dv01(instruments: Iterable, curve: ZeroCurve) -> float:
    instruments = list(instruments)
    base = portfolio_pv(instruments, curve)
    bumped = portfolio_pv(instruments, curve.shifted(1.0))
    return bumped - base


def key_rate_dv01(
    instruments: Iterable,
    curve: ZeroCurve,
    key_tenors: tuple[float, ...] = (1, 2, 5, 10, 20, 30),
    width: float = 2.0,
) -> dict[float, float]:
    instruments = list(instruments)
    base = portfolio_pv(instruments, curve)
    return {
        key: portfolio_pv(instruments, curve.shifted(1.0, center=key, width=width)) - base
        for key in key_tenors
        if curve.times[0] <= key <= curve.times[-1]
    }


def key_rate_duration(instruments: Iterable, curve: ZeroCurve, **kwargs) -> dict[float, float]:
    instruments = list(instruments)
    pv = portfolio_pv(instruments, curve)
    return {k: -v / (pv * 1e-4) for k, v in key_rate_dv01(instruments, curve, **kwargs).items()}
