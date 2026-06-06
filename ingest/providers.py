from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Any

from app.models import DataSource


class SyntheticProvider:

    source = DataSource(
        source_id="synthetic",
        name="Synthetic Generator",
        description="Deterministic offline OHLCV generator for development/demo.",
        base_url=None,
        kind="open",
    )

    def fetch(
        self, symbol: str, start: datetime, days: int = 60, base_price: float = 100.0
    ) -> list[dict[str, Any]]:
        rng = random.Random(hash(symbol) & 0xFFFFFFFF)
        price = base_price
        out: list[dict[str, Any]] = []
        for i in range(days):
            date = start + timedelta(days=i)
            if date.weekday() >= 5:  # skip weekends — markets are closed
                continue
            drift = math.sin(i / 9.0) * 0.4
            change = rng.gauss(drift, 1.5)
            open_p = round(price, 2)
            close_p = round(max(1.0, price + change), 2)
            high_p = round(max(open_p, close_p) + abs(rng.gauss(0, 0.7)), 2)
            low_p = round(min(open_p, close_p) - abs(rng.gauss(0, 0.7)), 2)
            volume = int(abs(rng.gauss(1_000_000, 250_000)))
            out.append(
                {
                    "observation_date": date,
                    "indicators": {
                        "open": open_p,
                        "high": high_p,
                        "low": low_p,
                        "close": close_p,
                        "volume": volume,
                    },
                }
            )
            price = close_p
        return out


class YFinanceProvider:

    source = DataSource(
        source_id="yfinance",
        name="Yahoo Finance (yfinance)",
        description="Daily OHLCV via the yfinance library.",
        base_url="https://finance.yahoo.com",
        kind="open",
    )

    def fetch(
        self, symbol: str, start: datetime, days: int = 60, **_: Any
    ) -> list[dict[str, Any]]:
        import yfinance as yf

        end = start + timedelta(days=days)
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
        out: list[dict[str, Any]] = []
        for ts, row in df.iterrows():
            out.append(
                {
                    "observation_date": ts.to_pydatetime(),
                    "indicators": {
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "adj_close": float(row["Adj Close"]),  # extra indicator!
                        "volume": int(row["Volume"]),
                    },
                }
            )
        return out


PROVIDERS = {
    "synthetic": SyntheticProvider,
    "yfinance": YFinanceProvider,
}
