"""축1. 차트 흐름 (기술적). pandas/ta 로 계산 후 쉬운 키워드로 번역."""
from __future__ import annotations

import pandas as pd

from . import indicators as ind
from .keywords import badge


def analyze(df: pd.DataFrame) -> dict:
    close = df["close"]
    ma = ind.moving_averages(close)
    rsi = ind.rsi(close)
    macd = ind.macd(close)
    bb = ind.bollinger(close)
    vol_ratio = ind.volume_ratio(df["volume"])
    sigma = ind.daily_volatility(close)
    support, resistance = ind.support_resistance(close)

    metrics = {
        "last": int(close.iloc[-1]),
        "ma": {w: [None if pd.isna(x) else round(float(x), 2) for x in s] for w, s in ma.items()},
        "rsi14": round(float(rsi.iloc[-1]), 1),
        "macd": {
            "macd": round(float(macd["macd"].iloc[-1]), 1),
            "signal": round(float(macd["signal"].iloc[-1]), 1),
            "hist": round(float(macd["hist"].iloc[-1]), 1),
            "cross_up": bool(macd["macd"].iloc[-1] > macd["signal"].iloc[-1]),
        },
        "bbands": {k: round(float(bb[k].iloc[-1]), 3 if k == "pct_b" else 1)
                   for k in ("mid", "upper", "lower", "pct_b")},
        "vol_ratio": vol_ratio,
        "sigma": round(sigma, 4),
        "atr": round(ind.atr(df), 1),
        "support": support,
        "resistance": resistance,
    }
    return {"metrics": metrics, "badges": _badges(metrics)}


def _badges(t: dict) -> list[dict]:
    b: list[dict] = []
    ma5 = t["ma"][5][-1]
    ma20 = t["ma"][20][-1]
    if ma5 and ma20:
        if ma5 > ma20:
            b.append(badge("상승 흐름 시작", "골든크로스(5일선>20일선)", "중",
                           "거래량이 함께 늘지 않으면 되돌림 가능"))
        else:
            b.append(badge("흐름 꺾임", "데드크로스(5일선<20일선)", "중",
                           "단기 저점에서 반등 나올 수 있음"))
    r = t["rsi14"]
    if r >= 70:
        b.append(badge("너무 많이 올랐어요, 단기과열", f"RSI {r} (과열)", "중",
                       "강세장에선 과열이 더 이어지기도 함"))
    elif r <= 30:
        b.append(badge("바닥 다지는 중", f"RSI {r} (과매도)", "중",
                       "추세 하락이면 과매도가 길어질 수 있음"))
    else:
        b.append(badge("보통 흐름", f"RSI {r} (중립)", "하", "방향성 약함 — 단독 판단 금지"))
    if t["macd"]["cross_up"]:
        b.append(badge("힘이 붙는 중", "MACD 시그널 상향", "하", "0선 아래면 신뢰도 낮음"))
    else:
        b.append(badge("힘이 빠지는 중", "MACD 시그널 하향", "하", "0선 위면 눌림일 수 있음"))
    if t["vol_ratio"] >= 1.6:
        b.append(badge("거래 폭발", f"거래량 20일평균 대비 {t['vol_ratio']}배", "중",
                       "급등 후 거래폭발은 고점 신호일 수도"))
    pb = t["bbands"]["pct_b"]
    if pb >= 0.95:
        b.append(badge("밴드 상단 과열", "볼린저 상단 이탈", "하", "밴드 워킹 가능"))
    elif pb <= 0.05:
        b.append(badge("밴드 하단 눌림", "볼린저 하단 이탈", "하", "추세 하락 지속 주의"))
    return b
