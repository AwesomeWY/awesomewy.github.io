"""분석 결과 응답 스키마 (프론트엔드와의 계약).

프론트엔드(assets/app.js)는 이 스키마 그대로의 JSON을 '표시'만 한다.
data/*.json 샘플과 /api/analyze 응답은 동일한 구조를 갖는다.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Signal = Literal["watch", "neutral", "caution"]        # 🟢🟡🔴
Risk = Literal["low", "medium", "high"]                # 낮음/보통/높음
Confidence = Literal["상", "중", "하"]                  # 신뢰도


class Badge(BaseModel):
    """초보자용 '쉬운 키워드' 배지. 원래 용어는 raw 로 부기."""
    key: str                      # 쉬운 키워드 (예: "상승 흐름 시작")
    raw: str                      # 원래 용어/근거 (예: "골든크로스(5>20)")
    confidence: Confidence        # 신뢰도 상·중·하
    counter_risk: str             # 반대 리스크 (신호가 틀릴 수 있는 이유)


class Conflict(BaseModel):
    exists: bool
    note: str = ""


class Verdict(BaseModel):
    signal: Signal
    signal_label: str
    signal_emoji: str
    risk_grade: Risk
    risk_label: str
    one_liner: str                # 한 줄 요약 (쉬운 말)
    combo: str                    # 성장×안정×가격 조합 (예: "고성장+고안정+저평가")
    confidence: Confidence
    conflict: Conflict


class Ranges(BaseModel):
    buy_zone: tuple[int, int]     # 매수 관심 구간 [하단, 상단]
    stop_loss: int                # 손절 기준(참고)
    target_zone: tuple[int, int]  # 목표 구간 [하단, 상단]
    invalidation: list[str]       # 판단을 바꿀 조건
    basis: str                    # 산출 근거 (확정가 아님 명시)


class Axis(BaseModel):
    badges: list[Badge]
    metrics: dict
    score: Optional[int] = None   # 성장성/안정성만 0~100 점수 사용


class Axes(BaseModel):
    technical: Axis
    flow: Axis
    growth: Axis
    stability: Axis
    valuation: Axis


class Meta(BaseModel):
    code: str
    name: str
    market: str
    sector: str
    as_of: str                    # 기준 시점 (장 마감일)
    generated_at: str             # 분석 생성 시각
    currency: str = "KRW"
    price: int
    sources: list[str]
    is_sample: bool = False


class ChartData(BaseModel):
    ohlcv: list[dict]
    ma: dict[str, list[Optional[float]]]


class AnalysisResult(BaseModel):
    meta: Meta
    verdict: Verdict
    ranges: Ranges
    axes: Axes
    chart: ChartData
    disclaimer: str = "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다."
