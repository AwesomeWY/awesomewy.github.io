"""분석 오케스트레이터: 데이터 수집 → 4축 계산 → 종합 판정 → 스키마 조립."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import (
    axis1_technical,
    axis2_flow,
    axis3_fundamental,
    axis4_valuation,
    data_sources,
    scoring,
)

DISCLAIMER = "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다."


def analyze(code: str) -> dict:
    name, market, sector = data_sources.fetch_market_and_sector(code)
    df = data_sources.fetch_ohlcv(code)
    flow_df = data_sources.fetch_investor_flow(code)
    fin = data_sources.fetch_financials(code)  # {growth..., stability..., valuation...}

    tech = axis1_technical.analyze(df)
    flow = axis2_flow.analyze(flow_df)
    growth = axis3_fundamental.growth(fin["growth"])
    stability = axis3_fundamental.stability(fin["stability"])
    valuation = axis4_valuation.analyze(fin["valuation"])

    v = scoring.verdict(tech, flow, growth, stability, valuation)
    rng = scoring.ranges(tech)

    as_of = df.index[-1]
    as_of_str = as_of.strftime("%Y-%m-%d") if hasattr(as_of, "strftime") else str(as_of)

    return {
        "meta": {
            "code": code, "name": name, "market": market, "sector": sector,
            "as_of": as_of_str,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "currency": "KRW", "price": int(df["close"].iloc[-1]),
            "sources": ["KRX 시세(pykrx)", "DART 재무(OpenDartReader)"],
            "is_sample": False,
        },
        "verdict": v,
        "ranges": rng,
        "axes": {
            "technical": tech, "flow": flow,
            "growth": growth, "stability": stability, "valuation": valuation,
        },
        "chart": {
            "ohlcv": _ohlcv_records(df),
            "ma": {str(w): tech["metrics"]["ma"][w] for w in (5, 20, 60, 120)},
        },
        "disclaimer": DISCLAIMER,
    }


def _ohlcv_records(df: pd.DataFrame) -> list[dict]:
    out = []
    for idx, row in df.tail(160).iterrows():
        d = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        out.append({"d": d, "o": int(row["open"]), "h": int(row["high"]),
                    "l": int(row["low"]), "c": int(row["close"]), "v": int(row["volume"])})
    return out
