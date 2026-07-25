"""축3. 회사 체력 (펀더멘탈) — '성장성'과 '안정성'을 분리해 각각 0~100 점수화.

입력값은 일부가 None 일 수 있다(DART 요약 재무엔 이자비용·현금흐름이 없을 수 있음).
None 은 '정보 없음'으로 취급해 점수 계산에서 제외하고, 배지에 부기한다.
※ 일회성 손익 제외(경상이익 기준)로 성장 지표를 계산해 넣는 것을 전제로 한다.
"""
from __future__ import annotations

from .keywords import badge


def _clip(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _num(x, default=None):
    return default if x is None else x


def growth(fin: dict) -> dict:
    rev = fin.get("rev_cagr_3y")
    op = fin.get("op_growth_yoy")
    eps = fin.get("eps_growth_yoy")
    margin = fin.get("op_margin_trend", "정보 부족")

    missing = [k for k, v in (("매출성장", rev), ("영업이익성장", op), ("EPS성장", eps)) if v is None]
    score = 50 + _num(rev, 0) * 120 + _num(op, 0) * 60 + _num(eps, 0) * 50
    score += {"개선": 8, "정체": 0, "악화": -12}.get(margin, 0)
    score = _clip(score)

    badges: list[dict] = []
    if rev is not None:
        if rev >= 0.20:
            badges.append(badge("쑥쑥 크는 회사", f"매출 3년 연평균 {rev*100:.0f}%", "상",
                                "전방 수요 둔화 시 성장률 급감 위험"))
        elif rev <= -0.02:
            badges.append(badge("성장 멈춤(역성장)", f"매출 3년 연평균 {rev*100:.0f}%", "중",
                                "업황 바닥에서 턴어라운드 가능성은 별도 점검"))
        else:
            badges.append(badge("꾸준히 크는 회사", f"매출 3년 연평균 {rev*100:.0f}%", "중",
                                "업황 사이클 둔화 시 흔들릴 수 있음"))
    peg = fin.get("peg")
    if eps is not None and eps <= 0:
        badges.append(badge("PEG 적용 불가", "성장률이 음수라 PEG 계산 의미 없음", "상",
                            "성장 회복 시 재평가 대상"))
    elif peg is not None and peg > 1.8:
        badges.append(badge("성장 대비 비쌈", f"PEG {peg} (성장보다 가격이 앞섬)", "중",
                            "성장 가속되면 PEG 정당화될 수도"))
    if missing:
        badges.append(badge("일부 성장 지표 정보 부족", "미확보: " + ", ".join(missing), "하",
                            "확보되는 대로 점수 신뢰도 상승"))
    return {"score": score, "metrics": fin, "badges": badges}


def stability(fin: dict) -> dict:
    debt = fin.get("debt_ratio")
    cur = fin.get("current_ratio")
    icov = fin.get("interest_coverage")
    fcf_pos = fin.get("fcf_positive")
    ocf_ni = fin.get("ocf_vs_ni")

    score = 50.0
    if debt is not None:
        score += (1.0 - debt) * 30
    if cur is not None:
        score += (cur - 1.0) * 15
    if icov is not None:
        score += min(icov, 20) * 1.0
    if fcf_pos is not None:
        score += 8 if fcf_pos else -8
    if ocf_ni is not None:
        score += (ocf_ni - 1.0) * 10
    if fin.get("is_capital_impaired"):
        score -= 40
    if fin.get("is_watch_issue"):
        score -= 25
    score = _clip(score)

    badges: list[dict] = []
    if debt is not None:
        if debt <= 0.5:
            badges.append(badge("재무 튼튼",
                                f"부채비율 {debt*100:.0f}%" + (f" · 유동비율 {cur*100:.0f}%" if cur else ""),
                                "상", "대규모 설비투자 시 현금흐름 변동 가능"))
        elif debt >= 1.0:
            badges.append(badge("빚 부담 큼, 주의", f"부채비율 {debt*100:.0f}%", "중",
                                "증설 투자 성격이면 성장기 부채는 무조건 나쁘진 않음"))
    if ocf_ni is not None:
        if ocf_ni >= 1.05:
            badges.append(badge("이익의 질 좋음", f"영업현금흐름이 순이익보다 큼({ocf_ni}배)", "상",
                                "일시적 운전자본 효과일 수 있어 추세 확인 필요"))
        elif ocf_ni < 0.8:
            badges.append(badge("이익의 질 주의", f"영업현금흐름이 순이익보다 작음({ocf_ni}배)", "중",
                                "매출채권·재고 증가로 인한 일시적 현상일 수 있음"))
    if fcf_pos is False:
        badges.append(badge("현금 나가는 중(투자기)", "잉여현금흐름(FCF) 마이너스", "중",
                            "설비투자 마무리되면 개선 가능"))
    if fin.get("is_capital_impaired"):
        badges.append(badge("적자 위험(자본잠식)", "자본총계 마이너스", "상", "즉시 재무 구조 확인 필요"))
    if fin.get("is_watch_issue"):
        badges.append(badge("관리종목 주의", "관리종목 지정", "상", "상장폐지 리스크 별도 점검"))

    missing = [k for k, v in (("이자보상배율", icov), ("FCF", fcf_pos), ("이익의 질", ocf_ni)) if v is None]
    if missing:
        badges.append(badge("일부 안정성 지표 정보 부족", "미확보: " + ", ".join(missing), "하",
                            "요약 재무 한계 — 상세 재무(현금흐름표) 연동 시 보완"))
    return {"score": score, "metrics": fin, "badges": badges}
