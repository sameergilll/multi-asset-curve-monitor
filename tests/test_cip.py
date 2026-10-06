import numpy as np
from curve_monitor.curves import ZeroCurve
from curve_monitor.cip import theoretical_forward, cip_deviation


def curve(rate):
    t=np.array([0.25,0.5,1,2,5])
    return ZeroCurve(t, np.exp(-rate*t))


def test_cip_formula():
    eur, usd = curve(0.02), curve(0.04)
    f = theoretical_forward(1.10, 1.0, eur, usd)
    assert abs(f - 1.10*np.exp(0.02)) < 1e-8


def test_zero_deviation_at_theoretical_forward():
    eur, usd = curve(0.02), curve(0.04)
    f = theoretical_forward(1.10, 1.0, eur, usd)
    r = cip_deviation(1.10, f, 1.0, eur, usd)
    assert abs(r.implied_basis_bp) < 1e-8
    assert r.signal == "within threshold"
