import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from curve_monitor.cip import cip_deviation
from curve_monitor.data import load_demo_curve, load_demo_fx_forwards, fetch_us_treasury_par_curve, fetch_spot_fx
from curve_monitor.instruments import FixedRateBond
from curve_monitor.risk import portfolio_pv, dv01, key_rate_dv01, key_rate_duration
from curve_monitor.scenarios import parallel_scenario, steepener_scenario

st.set_page_config(page_title="Multi-Asset Curve Monitor", page_icon="📈", layout="wide")
st.title("Multi-Asset Yield Curve & Cross-Currency FX Swap Monitor")
st.caption("Bootstrapped curves • DV01 / key-rate risk • CIP basis • scenario stress testing")

mode = st.sidebar.radio("Data mode", ["Deterministic demo", "Live public data"], index=0)

@st.cache_data(ttl=900)
def live_usd():
    return fetch_us_treasury_par_curve()

@st.cache_data(ttl=900)
def live_spot(base, quote):
    return fetch_spot_fx(base, quote)

usd = load_demo_curve("USD")
eur = load_demo_curve("EUR")
gbp = load_demo_curve("GBP")
source_note = "Bundled reproducible market snapshot"
if mode == "Live public data":
    try:
        usd, usd_date = live_usd()
        source_note = f"USD: U.S. Treasury ({usd_date}); non-USD curves: bundled snapshot"
    except Exception as exc:
        st.warning(f"Live Treasury fetch unavailable; using demo USD curve. {exc}")

st.info(source_note)

tab1, tab2, tab3, tab4 = st.tabs(["Yield Curves", "CIP / FX Swaps", "DV01 & KRD", "Stress Tests"])

with tab1:
    fig = go.Figure()
    for name, curve in [("USD", usd), ("EUR", eur), ("GBP", gbp)]:
        x = np.linspace(curve.times[0], curve.times[-1], 180)
        fig.add_scatter(x=x, y=curve.zero_rate(x)*100, mode="lines", name=name)
    fig.update_layout(xaxis_title="Maturity (years)", yaxis_title="Zero rate (%)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    cols = st.columns(3)
    for col, (name, curve) in zip(cols, [("USD", usd), ("EUR", eur), ("GBP", gbp)]):
        with col:
            st.metric(f"{name} 2Y zero", f"{curve.zero_rate(2)*100:.2f}%")
            st.metric(f"{name} 10Y zero", f"{curve.zero_rate(10)*100:.2f}%")

with tab2:
    df = load_demo_fx_forwards()
    pair = st.selectbox("FX pair", sorted(df.pair.unique()))
    row = df[df.pair == pair].iloc[0]
    curves = {"USD": usd, "EUR": eur, "GBP": gbp}
    base, quote = pair[:3], pair[3:]
    spot = float(row.spot)
    if mode == "Live public data":
        try:
            spot, spot_date = live_spot(base, quote)
            st.caption(f"Spot from Frankfurter official-source feed: {spot_date}")
        except Exception as exc:
            st.warning(f"Live FX spot unavailable; using bundled spot. {exc}")
    market_forward = st.number_input("Observed market forward", value=float(row.market_forward), format="%.6f")
    tenor = st.select_slider("Tenor (years)", options=[0.25, 0.5, 1.0, 2.0], value=float(row.tenor_years))
    result = cip_deviation(spot, market_forward, tenor, curves[base], curves[quote])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot", f"{spot:.5f}")
    c2.metric("CIP fair forward", f"{result.theoretical_forward:.5f}")
    c3.metric("Deviation", f"{result.deviation_pips:+.1f} pips")
    c4.metric("Implied basis", f"{result.implied_basis_bp:+.1f} bp")
    st.write(f"**Signal:** {result.signal}")
    st.caption("Observed forward points are intentionally user-editable: institutional FX-swap feeds are typically licensed; the repository remains reproducible without proprietary data.")

with tab3:
    n5 = st.number_input("5Y bond notional", min_value=0, value=10_000_000, step=500_000)
    n10 = st.number_input("10Y bond notional", min_value=0, value=7_500_000, step=500_000)
    portfolio = [FixedRateBond(n5, 5.0, 0.04), FixedRateBond(n10, 10.0, 0.045)]
    pv = portfolio_pv(portfolio, usd)
    risk = dv01(portfolio, usd)
    kr = key_rate_dv01(portfolio, usd)
    krd = key_rate_duration(portfolio, usd)
    c1, c2 = st.columns(2)
    c1.metric("Portfolio PV", f"${pv:,.0f}")
    c2.metric("Parallel DV01", f"${risk:,.0f} / bp")
    risk_df = pd.DataFrame({"Tenor": list(kr), "Key-rate DV01": list(kr.values()), "Key-rate duration": [krd[k] for k in kr]})
    st.dataframe(risk_df, use_container_width=True, hide_index=True)
    st.bar_chart(risk_df.set_index("Tenor")["Key-rate DV01"])

with tab4:
    portfolio = [FixedRateBond(10_000_000, 5.0, 0.04), FixedRateBond(7_500_000, 10.0, 0.045)]
    shift = st.slider("Parallel rate shock (bp)", -100, 100, 25, 5)
    p = parallel_scenario(portfolio, usd, shift)
    s = steepener_scenario(portfolio, usd)
    scenarios = pd.DataFrame([
        {"Scenario": f"Parallel {shift:+d} bp", "P&L": p["pnl"]},
        {"Scenario": "10s/short-end steepener", "P&L": s["pnl"]},
    ])
    st.dataframe(scenarios.style.format({"P&L": "${:,.0f}"}), use_container_width=True, hide_index=True)
    st.bar_chart(scenarios.set_index("Scenario"))
