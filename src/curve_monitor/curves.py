from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

try:
    import QuantLib as ql
except ImportError:  # pragma: no cover
    ql = None


@dataclass(frozen=True)
class CurveNode:
    tenor_years: float
    par_rate: float


class ZeroCurve:
    """Continuously-compounded zero curve with log-discount interpolation."""

    def __init__(self, times: Iterable[float], discount_factors: Iterable[float]):
        t = np.asarray(list(times), dtype=float)
        df = np.asarray(list(discount_factors), dtype=float)
        if len(t) < 2 or len(t) != len(df):
            raise ValueError("times and discount_factors must have equal length >= 2")
        if np.any(t <= 0) or np.any(np.diff(t) <= 0):
            raise ValueError("times must be strictly increasing and positive")
        if np.any((df <= 0) | (df > 1.5)):
            raise ValueError("discount factors must be positive and plausible")
        self.times = t
        self.discount_factors = df
        self._log_df = PchipInterpolator(t, np.log(df), extrapolate=True)

    def discount(self, t: float | np.ndarray) -> float | np.ndarray:
        arr = np.asarray(t, dtype=float)
        if np.any(arr < 0):
            raise ValueError("time cannot be negative")
        out = np.ones_like(arr)
        positive = arr > 0
        out[positive] = np.exp(self._log_df(arr[positive]))
        return float(out) if out.ndim == 0 else out

    def zero_rate(self, t: float | np.ndarray) -> float | np.ndarray:
        arr = np.asarray(t, dtype=float)
        out = np.zeros_like(arr)
        positive = arr > 0
        out[positive] = -np.log(self.discount(arr[positive])) / arr[positive]
        return float(out) if out.ndim == 0 else out

    def shifted(self, bump_bp: float, center: float | None = None, width: float = 2.0) -> "ZeroCurve":
        rates = self.zero_rate(self.times)
        bump = bump_bp / 10_000.0
        if center is None:
            weights = np.ones_like(self.times)
        else:
            weights = np.clip(1.0 - np.abs(self.times - center) / width, 0.0, 1.0)
        shifted_rates = rates + bump * weights
        return ZeroCurve(self.times, np.exp(-shifted_rates * self.times))

    def to_quantlib(self, valuation_date: date | None = None):
        """Create a QuantLib ZeroCurve for independent analytics/validation."""
        if ql is None:
            raise RuntimeError("QuantLib is not installed")
        valuation_date = valuation_date or date.today()
        ql_date = ql.Date(valuation_date.day, valuation_date.month, valuation_date.year)
        dates = [ql_date]
        rates = [float(self.zero_rate(self.times[0]))]
        for t, r in zip(self.times, self.zero_rate(self.times)):
            days = max(1, int(round(float(t) * 365.0)))
            dates.append(ql_date + days)
            rates.append(float(r))
        return ql.ZeroCurve(dates, rates, ql.Actual365Fixed(), ql.NullCalendar())


def bootstrap_par_curve(nodes: Iterable[CurveNode], coupon_frequency: int = 2) -> ZeroCurve:
    """Bootstrap discount factors from money-market/par-yield nodes.

    Nodes below one coupon period are treated as continuously-compounded money-market
    zero rates. For coupon-bearing maturities, the terminal discount factor is solved
    so the par bond prices to 100. Intermediate coupon DFs are log-linearly interpolated
    between the last solved node and the candidate terminal DF.
    """
    nodes = sorted(nodes, key=lambda n: n.tenor_years)
    if len(nodes) < 2:
        raise ValueError("at least two curve nodes are required")
    if any(n.tenor_years <= 0 for n in nodes):
        raise ValueError("tenors must be positive")

    solved_t: list[float] = []
    solved_df: list[float] = []
    step = 1.0 / coupon_frequency

    def known_discount(x: float, terminal_t: float, terminal_df: float) -> float:
        if not solved_t:
            return float(np.exp(-terminal_t * 0.0))
        if x <= solved_t[-1]:
            if len(solved_t) == 1:
                z = -np.log(solved_df[0]) / solved_t[0]
                return float(np.exp(-z * x))
            return float(np.exp(np.interp(x, solved_t, np.log(solved_df))))
        # Log-linear interpolation to the candidate terminal node.
        w = (x - solved_t[-1]) / (terminal_t - solved_t[-1])
        return float(np.exp((1 - w) * np.log(solved_df[-1]) + w * np.log(terminal_df)))

    for node in nodes:
        t, r = float(node.tenor_years), float(node.par_rate)
        if t <= step + 1e-12:
            df = float(np.exp(-r * t))
        else:
            coupon = r / coupon_frequency
            cashflow_times = np.arange(step, t + 1e-10, step)
            if len(cashflow_times) == 0 or abs(cashflow_times[-1] - t) > 1e-7:
                cashflow_times = np.append(cashflow_times[cashflow_times < t], t)

            def price_error(terminal_df: float) -> float:
                pv_coupons = sum(
                    coupon * known_discount(float(ct), t, terminal_df)
                    for ct in cashflow_times[:-1]
                )
                return pv_coupons + (1.0 + coupon) * terminal_df - 1.0

            lo, hi = 1e-6, 1.25
            if price_error(lo) * price_error(hi) > 0:
                raise ValueError(f"could not bootstrap maturity {t}y")
            df = float(brentq(price_error, lo, hi, xtol=1e-13))
        solved_t.append(t)
        solved_df.append(df)

    return ZeroCurve(solved_t, solved_df)
