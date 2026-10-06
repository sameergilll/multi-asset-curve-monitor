from __future__ import annotations

import numpy as np
from .curves import ZeroCurve


def curve_shift_alerts(old: ZeroCurve, new: ZeroCurve, threshold_bp: float = 5.0) -> list[dict]:
    tenors = sorted(set(old.times).intersection(set(new.times)))
    alerts = []
    for t in tenors:
        move_bp = (new.zero_rate(t) - old.zero_rate(t)) * 10_000
        if abs(move_bp) >= threshold_bp:
            alerts.append({"tenor_years": float(t), "move_bp": float(move_bp), "direction": "up" if move_bp > 0 else "down"})
    return alerts
