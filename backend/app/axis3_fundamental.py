"""축3. 회사 체력 (펀더멘탈) — '성장성'과 '안정성'을 분리해 각각 0~100 점수화.

입력 fin(dict) 규격 (data_sources.fetch_financials 산출):
  rev_cagr_3y, op_growth_yoy, op_margin_trend('개선'/'정체'/'악화'),
  eps_growth_yoy, peg(None 가능),
  debt_ratio, current_ratio, interest_coverage,
  fcf_positive(bool), ocf_vs_ni(영업현금흐름/순이익),
  is_capital_impaired(bool), is_watch_issue(bool)
※ 일회성 손익 제외(경상이익 기준)로 성장 지표를 계산해 넣을 것.
"""
from __future__ import annotations

from .keywords import badge


def _clip(x: float) -> int:
    return int(max(0, min(100, round(x))))


def growth(fin: dict) -> dict:
    rev = fin.get("rev_cagr_3y") or 0.0
    op = fin.get("op_growth_yoy") or 0.0
    eps = fin.get("eps_growth_yoy") or 0.0
    margin = fin.get("op_margin_trend", "정체")

    # 성장 점수: 매출CAGR·영업이익·EPS 성장률 가중 + 이익률 추세 보정
    score = 50 + rev * 120 + op * 60 + eps * 50
    score += {"개선": 8, "정체": 0, "악화": -12}.get(margin, 0)
    score = _clip(score)

    badges: list[dict] = []
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
    if peg is None:
        badges.append(badge("PEG 적용 불가", "성장률이 음수라 PEG 계산 의미 없음", "상",
                            "성장 회복 시 재평가 대상"))
    elif peg > 1.8:
        badges.append(badge("성장 대비 비쌈", f"PEG {peg} (성장보다 가격이 앞섬)", "중",
                            "성장 가속되면 PEG 정당화될 수도"))
    return {"score": score, "metrics": fin, "badges": badges}


def stability(fin: dict) -> dict:
    debt = fin.get("debt_ratio", 1.0)
    cur = fin.get("current_ratio", 1.0)
    icov = fin.get("interest_coverage", 1.0)
    fcf_pos = fin.get("fcf_positive", False)
    ocf_ni = fin.get("ocf_vs_ni", 1.0)

    score = 50
    score += (1.0 - debt) * 30          # 부채비율 낮을수록 +
    score += (cur - 1.0) * 15           # 유동비율 높을수록 +
    score += min(icov, 20) * 1.0        # 이자보상배율 (상한)
    score += 8 if fcf_pos else -8
    score += (ocf_ni - 1.0) * 10        # 이익의 질
    if fin.get("is_capital_impaired"):
        score -= 40
    if fin.get("is_watch_issue"):
        score -= 25
    score = _clip(score)

    badges: list[dict] = []
    if debt <= 0.5:
        badges.append(badge("재무 튼튼", f"부채비율 {debt*100:.0f}% · 유동비율 {cur*100:.0f}%", "상",
                            "대규모 설비투자 시 현금흐름 변동 가능"))
    elif debt >= 1.0:
        badges.append(badge("빚 부담 큼, 주의", f"부채비율 {debt*100:.0f}% · 이자보상배율 {icov}배", "중",
                            "증설 투자 성격이면 성장기 부채는 무조건 나쁘진 않음"))
    if ocf_ni >= 1.05:
        badges.append(badge("이익의 질 좋음", f"영업현금흐름이 순이익보다 큼({ocf_ni}배)", "상",
                            "일시적 운전자본 효과일 수 있어 추세 확인 필요"))
    elif ocf_ni < 0.8:
        badges.append(badge("이익의 질 주의", f"영업현금흐름이 순이익보다 작음({ocf_ni}배)", "중",
                            "매출채권·재고 증가로 인한 일시적 현상일 수 있음"))
    if not fcf_pos:
        badges.append(badge("현금 나가는 중(투자기)", "잉여현금흐름(FCF) 마이너스", "중",
                            "설비투자 마무리되면 개선 가능"))
    if fin.get("is_capital_impaired"):
        badges.append(badge("적자 위험(자본잠식)", "자본잠식 상태", "상", "즉시 재무 구조 확인 필요"))
    if fin.get("is_watch_issue"):
        badges.append(badge("관리종목 주의", "관리종목 지정", "상", "상장폐지 리스크 별도 점검"))
    return {"score": score, "metrics": fin, "badges": badges}
