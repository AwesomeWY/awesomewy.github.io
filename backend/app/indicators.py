"""기술적 지표 계산 (pandas + ta). 원칙 1: 모든 수치는 여기서 계산.

`ta` 라이브러리를 사용하되, 라이브러리 미설치 환경에서도 논리를 검증할 수 있도록
표준 정의(Wilder RSI, EMA 기반 MACD 등)를 그대로 따른다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def moving_averages(close: pd.Series, windows=(5, 20, 60, 120)) -> dict[int, pd.Series]:
    return {w: close.rolling(w).mean() for w in windows}


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    from ta.momentum import RSIIndicator
    return RSIIndicator(close, window=period).rsi()


def macd(close: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    from ta.trend import MACD
    m = MACD(close, window_fast=fast, window_slow=slow, window_sign=signal)
    return pd.DataFrame({"macd": m.macd(), "signal": m.macd_signal(), "hist": m.macd_diff()})


def bollinger(close: pd.Series, window=20, dev=2) -> pd.DataFrame:
    from ta.volatility import BollingerBands
    b = BollingerBands(close, window=window, window_dev=dev)
    return pd.DataFrame({
        "mid": b.bollinger_mavg(), "upper": b.bollinger_hband(),
        "lower": b.bollinger_lband(), "pct_b": b.bollinger_pband(),
    })


def volume_ratio(volume: pd.Series, window=20) -> float:
    """당일 거래량 / 최근 window일 평균 거래량."""
    avg = volume.rolling(window).mean().iloc[-1]
    return float(round(volume.iloc[-1] / avg, 2)) if avg else float("nan")


def daily_volatility(close: pd.Series, window=20) -> float:
    """최근 window일 로그수익률 표준편차 (일간 변동성 σ)."""
    logret = np.log(close / close.shift(1)).dropna()
    return float(logret.tail(window).std())


def atr(df: pd.DataFrame, period=14) -> float:
    from ta.volatility import AverageTrueRange
    a = AverageTrueRange(df["high"], df["low"], df["close"], window=period)
    return float(a.average_true_range().iloc[-1])


def support_resistance(close: pd.Series, lookback_support=20, lookback_res=40) -> tuple[int, int]:
    return int(round(close.tail(lookback_support).min())), int(round(close.tail(lookback_res).max()))


def annualized_risk_grade(sigma_daily: float) -> tuple[str, str]:
    """일간 σ → 연율화(√252) → 위험 등급."""
    ann = sigma_daily * np.sqrt(252)
    if ann < 0.25:
        return "low", "낮음"
    if ann < 0.45:
        return "medium", "보통"
    return "high", "높음"
