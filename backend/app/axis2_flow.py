"""축2. 수급 (외국인·기관 순매수 추이)."""
from __future__ import annotations

import pandas as pd

from .keywords import badge


def analyze(flow: pd.DataFrame) -> dict:
    """flow: index=날짜, 최소 컬럼 '외국인', '기관합계'(순매수 수량/금액)."""
    fcol = _pick(flow, ["외국인", "외국인합계"])
    icol = _pick(flow, ["기관합계", "기관"])

    def s(col, n):
        return int(flow[col].tail(n).sum()) if col else 0

    m = {
        "foreign_5d": s(fcol, 5), "foreign_20d": s(fcol, 20),
        "inst_5d": s(icol, 5), "inst_20d": s(icol, 20),
    }
    return {"metrics": m, "badges": _badges(m)}


def _pick(df: pd.DataFrame, names) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def _badges(m: dict) -> list[dict]:
    b: list[dict] = []
    f20 = m["foreign_20d"]
    if f20 > 0:
        b.append(badge("외국인이 사 모으는 중", f"외국인 20일 누적 순매수 {f20:+,}", "중",
                       "지수 리밸런싱 등 일시적 매수일 수 있음"))
    elif f20 < 0:
        b.append(badge("외국인 이탈 주의", f"외국인 20일 누적 {f20:+,}", "중",
                       "낙폭 과대 반등 시 단기 매수 유입 가능"))
    i20 = m["inst_20d"]
    if i20 > 0:
        b.append(badge("기관도 동참", f"기관 20일 순매수 {i20:+,}", "중", "차익실현 물량 유입 가능"))
    elif i20 < 0:
        b.append(badge("기관 이탈 주의", f"기관 20일 순매도 {i20:+,}", "중", "저점 매집 초입 가능성은 낮음"))
    else:
        b.append(badge("기관은 관망", "기관 순매수 중립", "하", "규모 작아 방향성으로 보기 어려움"))
    return b
