from __future__ import annotations

import argparse
import json
from .data import load_demo_curve, load_demo_fx_forwards
from .cip import cip_deviation
from .instruments import FixedRateBond
from .risk import dv01, key_rate_duration


def main() -> None:
    parser = argparse.ArgumentParser(description="Yield curve & cross-currency monitor")
    parser.add_argument("--demo", action="store_true", help="run bundled deterministic demo")
    args = parser.parse_args()
    if not args.demo:
        parser.print_help()
        return

    usd = load_demo_curve("USD")
    eur = load_demo_curve("EUR")
    portfolio = [FixedRateBond(10_000_000, 5.0, 0.04), FixedRateBond(7_500_000, 10.0, 0.045)]
    forwards = load_demo_fx_forwards()
    eurusd = forwards[forwards["pair"] == "EURUSD"].iloc[0]
    result = cip_deviation(float(eurusd.spot), float(eurusd.market_forward), float(eurusd.tenor_years), eur, usd)
    output = {
        "portfolio_dv01_usd": round(dv01(portfolio, usd), 2),
        "key_rate_duration": {str(k): round(v, 4) for k, v in key_rate_duration(portfolio, usd).items()},
        "eurusd_cip": {
            "market_forward": round(result.market_forward, 6),
            "theoretical_forward": round(result.theoretical_forward, 6),
            "basis_bp": round(result.implied_basis_bp, 2),
            "signal": result.signal,
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
