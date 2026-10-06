import numpy as np
from curve_monitor.curves import ZeroCurve
from curve_monitor.instruments import FixedRateBond, ZeroCouponBond
from curve_monitor.risk import portfolio_pv, dv01, key_rate_dv01
from curve_monitor.scenarios import parallel_scenario


def make_curve():
    t=np.array([0.25,0.5,1,2,3,5,7,10,20,30])
    return ZeroCurve(t, np.exp(-0.04*t))


def test_bond_pv_positive():
    assert FixedRateBond(1_000_000,5,0.04).pv(make_curve()) > 0


def test_zcb_pv_matches_discount():
    c=make_curve(); z=ZeroCouponBond(100,2)
    assert abs(z.pv(c)-100*c.discount(2)) < 1e-9


def test_dv01_negative_for_long_bond():
    assert dv01([FixedRateBond(1_000_000,10,0.04)], make_curve()) < 0


def test_key_rate_dv01_has_nodes():
    kr=key_rate_dv01([FixedRateBond(1_000_000,10,0.04)], make_curve())
    assert 5 in kr and 10 in kr


def test_positive_rate_shock_loses_money():
    result=parallel_scenario([FixedRateBond(1_000_000,10,0.04)], make_curve(), 25)
    assert result["pnl"] < 0


def test_portfolio_pv_additive():
    c=make_curve(); a=FixedRateBond(1_000_000,5,0.04); b=FixedRateBond(2_000_000,5,0.04)
    assert abs(portfolio_pv([a,b],c) - a.pv(c)-b.pv(c)) < 1e-6
