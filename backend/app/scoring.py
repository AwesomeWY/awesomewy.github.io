"""종합 판정 — 성장 × 안정 × 가격매력도 조합 + 차트/펀더 충돌 감지 + 참고 구간 산출."""
from __future__ import annotations

from .indicators import annualized_risk_grade
from .keywords import combo_label


def _chart_bias(tech: dict) -> int:
    """차트 신호를 -2(약세)~+2(강세) 로 요약."""
    t = tech["metrics"]
    score = 0
    ma5, ma20 = t["ma"][5][-1], t["ma"][20][-1]
    if ma5 and ma20:
        score += 1 if ma5 > ma20 else -1
    if t["macd"]["cross_up"]:
        score += 1
    else:
        score -= 1
    if t["rsi14"] >= 70:
        score -= 1  # 과열은 단기 부담
    elif t["rsi14"] <= 30:
        score += 1
    return max(-2, min(2, score))


def _fundamental_bias(growth: dict, stability: dict, valuation: dict) -> int:
    """펀더멘탈 신호를 -2~+2 로 요약. 점수 None(정보 부족)은 중립(50)으로 취급."""
    g = growth["score"] if growth.get("score") is not None else 50
    s = stability["score"] if stability.get("score") is not None else 50
    bucket = valuation.get("bucket", "적정가격")
    base = (g + s) / 100 - 1.0            # 0~2 → -1~+1 근처
    val_adj = {"저평가": 0.6, "적정가격": 0.0, "고평가": -0.6,
               "저평가(밸류트랩 의심)": -0.4}.get(bucket, 0)
    return max(-2, min(2, round(base * 2 + val_adj)))


def verdict(tech, flow, growth, stability, valuation) -> dict:
    chart = _chart_bias(tech)
    fund = _fundamental_bias(growth, stability, valuation)
    total = chart + fund

    if total >= 2:
        signal, label, emoji = "watch", "관심", "🟢"
    elif total <= -2:
        signal, label, emoji = "caution", "주의", "🔴"
    else:
        signal, label, emoji = "neutral", "중립", "🟡"

    # 밸류트랩은 강제로 주의 이상으로 낮추지 않되, 관심은 못 됨
    if valuation["metrics"]["value_trap"]["suspected"] and signal == "watch":
        signal, label, emoji = "neutral", "중립", "🟡"

    risk_grade, risk_label = annualized_risk_grade(tech["metrics"]["sigma"])
    fundamentals_known = growth.get("score") is not None and stability.get("score") is not None
    combo = combo_label(growth.get("score") or 50, stability.get("score") or 50, valuation["bucket"])
    if not fundamentals_known:
        combo += " · 재무 정보 부족"

    # 차트와 펀더멘탈이 반대 방향이면 충돌 표시 (원칙: 양쪽 표시, 판단은 사용자)
    conflict_exists = (chart >= 1 and fund <= -1) or (chart <= -1 and fund >= 1)
    if conflict_exists:
        note = "차트와 펀더멘탈이 서로 다른 방향을 가리킴 — 최종 판단은 사용자 몫."
    else:
        note = "차트·수급·펀더멘탈이 대체로 같은 방향."

    if abs(total) >= 3 and not conflict_exists and fundamentals_known:
        confidence = "상"
    elif abs(total) >= 1:
        confidence = "중"
    else:
        confidence = "하"
    if not fundamentals_known and confidence == "상":
        confidence = "중"

    return {
        "signal": signal, "signal_label": label, "signal_emoji": emoji,
        "risk_grade": risk_grade, "risk_label": risk_label,
        "combo": combo, "confidence": confidence,
        "one_liner": _one_liner(signal, growth, stability, valuation, chart),
        "conflict": {"exists": conflict_exists, "note": note},
    }


def _one_liner(signal, growth, stability, valuation, chart) -> str:
    if valuation["metrics"]["value_trap"]["suspected"]:
        return "PER만 보면 싸 보이지만, 실적이 꺾이는 중이라 '싼 데는 이유'가 있어 보여요."
    if signal == "watch":
        return "회사 체력과 흐름이 함께 좋은 편이에요. 다만 변동성과 가격 부담은 늘 확인하세요."
    if signal == "caution":
        return "지금은 신호가 약해요. 서두르지 말고 조건이 바뀌는지 지켜보는 게 좋아요."
    if chart >= 1 and stability["score"] >= 70:
        return "회사 체력은 튼튼한데, 단기적으로 조금 올라 있어요. 눌림을 기다려도 좋아요."
    return "뚜렷한 방향이 없어요. 한 지표만 보지 말고 여러 축을 함께 보세요."


def ranges(tech: dict) -> dict:
    """지지/저항 + 20일 변동성(ATR) 기반 참고 구간. 확정가 아님."""
    t = tech["metrics"]
    support, resistance = t["support"], t["resistance"]
    ma60 = t["ma"][60][-1]
    stop = int(round(ma60)) if ma60 else int(round(support * 0.95))
    return {
        "buy_zone": (int(support), int(round(t["ma"][20][-1] or support))),
        "stop_loss": stop,
        "target_zone": (int(resistance), int(round(resistance * 1.10))),
        "invalidation": [
            "외국인이 3거래일 연속 순매도로 전환하면 → 수급 근거 약화",
            f"종가가 {stop:,}원(60일선) 아래로 마감하면 → 추세 훼손",
        ],
        "basis": "지지/저항선 + 20일 변동성(ATR) 기반으로 계산한 '구간'. 확정 가격이 아님.",
    }
