from __future__ import annotations

from io import StringIO
from pathlib import Path
import requests
import pandas as pd

from .curves import CurveNode, bootstrap_par_curve

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

TENOR_MAP = {
    "1 Mo": 1/12, "2 Mo": 2/12, "3 Mo": 0.25, "4 Mo": 4/12, "6 Mo": 0.5,
    "1 Yr": 1.0, "2 Yr": 2.0, "3 Yr": 3.0, "5 Yr": 5.0, "7 Yr": 7.0,
    "10 Yr": 10.0, "20 Yr": 20.0, "30 Yr": 30.0,
}


def load_demo_curve(currency: str):
    df = pd.read_csv(DATA_DIR / "demo_curves.csv")
    subset = df[df["currency"].str.upper() == currency.upper()].sort_values("tenor_years")
    if subset.empty:
        raise ValueError(f"no demo curve for {currency}")
    nodes = [CurveNode(float(r.tenor_years), float(r.par_rate)) for r in subset.itertuples()]
    return bootstrap_par_curve(nodes)


def load_demo_fx_forwards() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "demo_fx_forwards.csv")


def fetch_us_treasury_par_curve(year: int | None = None, timeout: int = 12):
    """Fetch latest US Treasury par-yield row and bootstrap a USD curve."""
    year = year or pd.Timestamp.utcnow().year
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
    )
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "curve-monitor/1.0"})
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    if df.empty:
        raise RuntimeError("Treasury returned no observations")
    latest = df.iloc[0]
    nodes = []
    for col, tenor in TENOR_MAP.items():
        if col in latest and pd.notna(latest[col]):
            nodes.append(CurveNode(tenor, float(latest[col]) / 100.0))
    return bootstrap_par_curve(nodes), str(latest.get("Date", "latest"))


def fetch_spot_fx(base: str, quote: str, timeout: int = 8) -> tuple[float, str]:
    """Fetch daily official-source spot FX from Frankfurter v2 (no API key)."""
    url = f"https://api.frankfurter.dev/v2/rate/{base.lower()}/{quote.lower()}"
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "curve-monitor/1.0"})
    resp.raise_for_status()
    payload = resp.json()
    return float(payload["rate"]), str(payload["date"])
