import numpy as np
from curve_monitor.curves import CurveNode, ZeroCurve, bootstrap_par_curve


def test_flat_curve_bootstrap_is_close_to_flat():
    nodes = [CurveNode(t, 0.04) for t in [0.25, 0.5, 1, 2, 3, 5, 10]]
    curve = bootstrap_par_curve(nodes)
    assert np.all(np.diff(curve.discount_factors) < 0)
    assert abs(curve.zero_rate(5) - 0.04) < 0.003


def test_discount_at_zero_is_one():
    c = ZeroCurve([1, 2], [0.96, 0.92])
    assert c.discount(0) == 1.0


def test_parallel_shift_is_one_bp():
    c = ZeroCurve([1, 2, 5], np.exp(-0.04*np.array([1,2,5])))
    shifted = c.shifted(1)
    assert abs((shifted.zero_rate(2)-c.zero_rate(2))*1e4 - 1) < 1e-8


def test_quantlib_conversion():
    import pytest
    pytest.importorskip("QuantLib")
    c = ZeroCurve([1, 2, 5], np.exp(-0.04*np.array([1,2,5])))
    qlc = c.to_quantlib()
    assert qlc.discount(2.0) > 0
