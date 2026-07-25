"""분석 오케스트레이터: 데이터 수집 → 4축 계산 → 종합 판정 → 스키마 조립.

회복력 설계:
  - 축1(차트)·축2(수급)·축4(가격)는 KRX(pykrx)만으로 계산 → API 키 없이 항상 동작.
  - 축3(성장/안정)은 DART 재무가 있으면 계산, 없으면 '정보 부족'으로 우아하게 degrade.
"""
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
from .keywords import badge

DISCLAIMER = "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다."


def analyze(code: str) -> dict:
    name, market, sector = data_sources.fetch_market_and_sector(code)
    df = data_sources.fetch_ohlcv(code)

    # --- KRX 기반 (키 불필요) ---
    tech = axis1_technical.analyze(df)
    try:
        flow = axis2_flow.analyze(data_sources.fetch_investor_flow(code))
    except Exception:
        flow = _degraded_axis("수급 정보 없음", "투자자별 순매수 데이터를 불러오지 못했습니다.")
    val_market = data_sources.fetch_valuation(code, market)

    # --- DART 기반 (키 있으면 심화, 없으면 degrade) ---
    fin = data_sources.fetch_financials(code)
    if fin:
        growth = axis3_fundamental.growth(fin["growth"])
        stability = axis3_fundamental.stability(fin["stability"])
        earnings_declining = _is_declining(fin["growth"])
        peg = _peg(val_market.get("per"), fin["growth"].get("eps_growth_yoy"))
    else:
        growth = _degraded_axis(
            "재무 정보 없음",
            "DART 재무를 불러오지 못했습니다(DART_API_KEY 미설정 또는 공시 없음). "
            "성장성 점수는 유보합니다.")
        stability = _degraded_axis("재무 정보 없음", "재무 안정성 지표를 유보합니다.")
        earnings_declining = False
        peg = None

    valuation = axis4_valuation.analyze({
        **val_market,
        "peg": peg,
        "earnings_declining": earnings_declining,
        "psr": None, "ev_sales": None,
    })

    v = scoring.verdict(tech, flow, growth, stability, valuation)
    rng = scoring.ranges(tech)

    as_of = df.index[-1]
    as_of_str = as_of.strftime("%Y-%m-%d") if hasattr(as_of, "strftime") else str(as_of)
    sources = ["KRX 시세·수급·PER/PBR(pykrx)"]
    sources.append("DART 재무(OpenDartReader)" if fin else "DART 재무: 미연동")

    return {
        "meta": {
            "code": code, "name": name, "market": market, "sector": sector or "—",
            "as_of": as_of_str,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "currency": "KRW", "price": int(df["close"].iloc[-1]),
            "sources": sources, "is_sample": False,
        },
        "verdict": v,
        "ranges": rng,
        "axes": {"technical": tech, "flow": flow, "growth": growth,
                 "stability": stability, "valuation": valuation},
        "chart": {
            "ohlcv": _ohlcv_records(df),
            "ma": {str(w): tech["metrics"]["ma"][w] for w in (5, 20, 60, 120)},
        },
        "disclaimer": DISCLAIMER,
    }


def _degraded_axis(key: str, reason: str) -> dict:
    return {"score": None, "metrics": {"available": False},
            "badges": [badge(key, "데이터 부족", "하", reason)]}


def _peg(per, eps_growth_yoy):
    if per is None or eps_growth_yoy is None or eps_growth_yoy <= 0:
        return None
    return round(per / (eps_growth_yoy * 100), 2)


def _is_declining(g: dict) -> bool:
    op = g.get("op_growth_yoy")
    ni = g.get("eps_growth_yoy")
    return (op is not None and op < 0) or (ni is not None and ni < 0)


def _ohlcv_records(df: pd.DataFrame) -> list[dict]:
    out = []
    for idx, row in df.tail(160).iterrows():
        d = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        out.append({"d": d, "o": int(row["open"]), "h": int(row["high"]),
                    "l": int(row["low"]), "c": int(row["close"]), "v": int(row["volume"])})
    return out
