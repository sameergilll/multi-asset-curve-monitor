# Multi-Asset Yield Curve & Cross-Currency FX Swap Monitor

A production-style Python analytics project for bootstrapping zero-coupon curves, measuring fixed-income curve risk, monitoring covered-interest-parity (CIP) deviations in FX forwards, and stress-testing rate portfolios.

> Built as a portfolio project to demonstrate practical markets / trading analytics: curve construction, DV01 and key-rate risk, FX swap pricing, basis monitoring, public-data ingestion, testing, and dashboard delivery.

![Dashboard preview](assets/dashboard_preview.png)

## What the project does

- **Bootstraps zero-coupon discount curves** from money-market / par-yield nodes using `SciPy` root finding and shape-preserving interpolation.
- **Bridges curves into QuantLib** for independent curve representation and downstream quantitative-finance workflows.
- **Calculates portfolio PV, parallel DV01, key-rate DV01 and key-rate duration** for fixed-rate and zero-coupon bond exposures.
- **Prices theoretical FX forwards under Covered Interest Parity** and measures market-vs-fair deviations in pips and annualised basis points.
- **Flags cross-currency funding anomalies** when observed forward pricing moves outside a configurable basis threshold.
- **Runs scenario stresses**, including parallel rate shocks and curve steepeners.
- **Supports reproducible demo data and live public data**: U.S. Treasury par yields and key-free spot FX data.
- **Ships with automated tests and GitHub Actions CI** across Python 3.10–3.12.

## Architecture

```text
Public / bundled market data
        |
        v
+----------------------+       +----------------------+
| Curve construction   |------>| QuantLib bridge      |
| SciPy bootstrap      |       | zero-curve object    |
+----------+-----------+       +----------------------+
           |
     +-----+-------------------------+
     |                               |
     v                               v
+------------+                 +-------------------+
| Rates risk |                 | FX / CIP monitor  |
| PV / DV01  |                 | fair forwards     |
| KRD / KRDV |                 | basis / signals   |
+------+-----+                 +---------+---------+
       |                                 |
       +---------------+-----------------+
                       v
              +------------------+
              | Streamlit UI     |
              | stress dashboard |
              +------------------+
```

## Quick start

```bash
git clone <your-repository-url>
cd multi-asset-curve-monitor
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
streamlit run app.py
```

A deterministic command-line demo is also included:

```bash
curve-monitor --demo
```

Example output:

```json
{
  "portfolio_dv01_usd": -10959.49,
  "key_rate_duration": {
    "1": 0.0719,
    "2": 0.1765,
    "5": 2.5962,
    "10": 3.0099
  },
  "eurusd_cip": {
    "market_forward": 1.188,
    "theoretical_forward": 1.187583,
    "basis_bp": 3.51,
    "signal": "within threshold"
  }
}
```

## Dashboard

The Streamlit app contains four views:

1. **Yield Curves** — USD, EUR and GBP bootstrapped zero curves.
2. **CIP / FX Swaps** — editable observed forward, CIP-implied fair forward, pips deviation and implied basis.
3. **DV01 & KRD** — portfolio PV, parallel DV01, key-rate DV01 and key-rate duration.
4. **Stress Tests** — parallel rate shocks and a steepener scenario with mark-to-market P&L.

The app starts in **Deterministic demo** mode so it always works for a reviewer. **Live public data** mode refreshes the USD curve from the U.S. Treasury and spot FX from Frankfurter.

## Curve bootstrap methodology

For short money-market nodes, the engine converts quoted rates into discount factors directly. For coupon-bearing maturities, it solves the par-bond condition

\[
1 = \sum_{i=1}^{n-1} \frac{c}{m}D(t_i) + \left(1 + \frac{c}{m}\right)D(T)
\]

where `c` is the par coupon, `m` is coupon frequency, and `D(t)` is the discount factor. When a coupon date lies between solved pillars, log discount factors are interpolated. The terminal discount factor is then solved with `scipy.optimize.brentq`.

Continuous zero rates are recovered from

\[
z(T) = -\frac{\ln D(T)}{T}.
\]

## DV01 and key-rate risk

Parallel DV01 is calculated by revaluing the portfolio after a +1 bp shift to the entire zero curve:

\[
DV01 = PV_{+1bp} - PV_{base}.
\]

Key-rate DV01 applies a local triangular bump around each key tenor and revalues the portfolio. Key-rate duration is reported as

\[
KRD_k = -\frac{KRDV01_k}{PV \times 10^{-4}}.
\]

This gives a more useful view than a single duration number when the exposure is concentrated in specific curve buckets.

## Covered Interest Parity monitor

For a currency pair quoted as **quote currency per unit of base currency**, the theoretical FX forward is

\[
F_{CIP}(T) = S_0 \frac{D_{base}(T)}{D_{quote}(T)}.
\]

The monitor compares an observed market forward with the theoretical forward and converts the difference into an annualised implied basis:

\[
Basis_{bp} = \frac{\ln(F_{mkt}/F_{CIP})}{T}\times 10,000.
\]

A configurable threshold generates a simple rich / cheap / within-threshold signal.

## Data design

The repository deliberately separates **analytics** from **data licensing**:

- `data/demo_curves.csv` and `data/demo_fx_forwards.csv` make every analytics path reproducible.
- Live USD Treasury par yields are fetched from the U.S. Treasury public CSV endpoint.
- Live spot FX is fetched from Frankfurter's key-free public API, which aggregates official-source reference rates.
- Observed FX-forward / swap points remain editable or can be supplied by CSV/API adapter. Institutional forward-point feeds are commonly licensed, so the project does not pretend that a free spot-FX API is a professional FX-swap feed.

This is intentional: an employer can clone and run the project without credentials, while the architecture remains ready for Bloomberg, Refinitiv, CME, ICE or internal market-data adapters.

## Repository layout

```text
.
├── app.py
├── data/
│   ├── demo_curves.csv
│   └── demo_fx_forwards.csv
├── src/curve_monitor/
│   ├── alerts.py
│   ├── cip.py
│   ├── cli.py
│   ├── curves.py
│   ├── data.py
│   ├── instruments.py
│   ├── risk.py
│   └── scenarios.py
├── tests/
├── .github/workflows/ci.yml
├── pyproject.toml
└── requirements.txt
```

## Tests

```bash
pytest -q
```

The suite checks:

- curve monotonicity and bootstrap sanity;
- parallel curve shifts;
- QuantLib conversion when QuantLib is installed;
- CIP pricing identities;
- zero-basis behavior at the theoretical forward;
- bond PV and discounting;
- DV01 sign;
- key-rate output;
- stress-test P&L direction;
- portfolio PV additivity.

## Live-data caveat

This repository is an **analytics and monitoring demonstration**, not a trading system. Public reference-rate data can be delayed or revised and should not be used as executable pricing. Production deployment would require licensed market data, market-standard calendars/conventions per currency, instrument-level curve helpers, robust persistence, and controls around stale / missing quotes.

## Why this project

The aim is to show the workflow a markets analyst or trader actually cares about rather than a standalone pricing formula: ingest quotes, construct curves, turn them into risk, compare cross-currency pricing relationships, identify abnormal moves, and communicate the result through a dashboard.

## Tech stack

`Python` · `QuantLib` · `SciPy` · `NumPy` · `pandas` · `Plotly` · `Streamlit` · `pytest` · `GitHub Actions`

## License

MIT.
