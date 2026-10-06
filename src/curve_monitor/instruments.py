from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .curves import ZeroCurve


@dataclass(frozen=True)
class FixedRateBond:
    notional: float
    maturity_years: float
    coupon_rate: float
    frequency: int = 2

    def cashflows(self) -> tuple[np.ndarray, np.ndarray]:
        step = 1.0 / self.frequency
        times = np.arange(step, self.maturity_years + 1e-10, step)
        if len(times) == 0 or abs(times[-1] - self.maturity_years) > 1e-7:
            times = np.append(times[times < self.maturity_years], self.maturity_years)
        amounts = np.full(len(times), self.notional * self.coupon_rate / self.frequency)
        amounts[-1] += self.notional
        return times, amounts

    def pv(self, curve: ZeroCurve) -> float:
        times, amounts = self.cashflows()
        return float(np.sum(amounts * curve.discount(times)))


@dataclass(frozen=True)
class ZeroCouponBond:
    notional: float
    maturity_years: float

    def pv(self, curve: ZeroCurve) -> float:
        return self.notional * curve.discount(self.maturity_years)
