"""쉬운 키워드 번역 헬퍼 (원칙 3·4).

각 축 모듈이 지표값을 판정해 이 헬퍼로 '쉬운 키워드 배지'를 만든다.
배지는 항상 [근거(raw) / 신뢰도 / 반대 리스크]를 함께 담는다.
"""
from __future__ import annotations


def badge(key: str, raw: str, confidence: str, counter_risk: str) -> dict:
    assert confidence in ("상", "중", "하"), "신뢰도는 상·중·하"
    return {"key": key, "raw": raw, "confidence": confidence, "counter_risk": counter_risk}


# 조합 라벨: 성장/안정/가격 3요소를 한국어 조합 문구로.
def combo_label(growth_score: int, stability_score: int, valuation_bucket: str) -> str:
    g = "고성장" if growth_score >= 70 else "중성장" if growth_score >= 45 else "저성장"
    s = "고안정" if stability_score >= 70 else "중안정" if stability_score >= 45 else "저안정"
    return f"{g} + {s} + {valuation_bucket}"
