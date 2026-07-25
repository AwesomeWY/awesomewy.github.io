"""축4. 가격 매력도 — 3축 교차검증(상대·역사적·성장반영) + 밸류트랩 경고.

입력 val(dict) 규격:
  per(None=적자), pbr, psr, ev_sales, peg(None=성장률 음수),
  sector_per_pct(동종업계 PER 백분위 0~100),
  hist_per_pct(자기 3~5년 PER 밴드 내 위치 0~100),
  is_loss(bool), earnings_declining(bool)  # '싼 이유' 검증용
"""
from __future__ import annotations

from .keywords import badge


def analyze(val: dict) -> dict:
    is_loss = val.get("is_loss", False)
    method = "PSR·EV/Sales (적자기업)" if is_loss else "PER/PBR"
    if not is_loss and val.get("peg") is not None:
        method += " + PEG (성장주)"

    # 백분위가 없으면(정보 부족) 50으로 중립 취급하되 표시는 '—'.
    sector_pct = val.get("sector_per_pct")
    hist_pct = val.get("hist_per_pct")
    s_pct = 50 if sector_pct is None else sector_pct
    h_pct = 50 if hist_pct is None else hist_pct

    pbr = val.get("pbr") or 0
    # 저평가 여부: 상대·역사적 백분위가 모두 낮으면 '싸다' (적자기업엔 PER 논리 미적용)
    cheap = (not is_loss) and s_pct <= 30 and h_pct <= 35
    expensive = (not is_loss) and (s_pct >= 70 or pbr >= 5)

    # 밸류트랩 검증: 싸 보이지만 실적 악화면 경고 (원칙: 저평가면 '싼 이유' 검증)
    trap = cheap and val.get("earnings_declining", False)

    def pctxt(p):
        return "—" if p is None else f"{p}%"

    metrics = dict(val)
    metrics["method"] = method
    metrics["value_trap"] = {
        "suspected": bool(trap),
        "reason": ("PER·PBR은 하위권(싸다)이나 이익이 감소 추세 — 저평가가 아니라 "
                   "'실적 악화 반영'일 가능성") if trap else None,
    }

    badges: list[dict] = []
    per_pbr = f"PER {val.get('per') if val.get('per') is not None else '적자·N/A'} · PBR {val.get('pbr') or '—'}"
    if is_loss:
        badges.append(badge("적자 — 밸류 판단 보류",
                            f"{per_pbr} · PER 무의미, PSR/EV·Sales 필요", "중",
                            "흑자 전환·매출 성장 확인 시 재평가"))
    elif trap:
        badges.append(badge("싸지만 이유 있음",
                            f"{per_pbr} (밸류트랩 의심)", "중",
                            "업황 반등·구조조정 성공 시 진짜 저평가일 수 있음"))
    elif cheap:
        badges.append(badge("지금 싼 편",
                            f"상대 PER 백분위 {pctxt(sector_pct)} · 역사적 밴드 {pctxt(hist_pct)}", "중",
                            "싼 데는 이유가 있을 수 있으니 실적 추세 재확인"))
    elif expensive:
        badges.append(badge("비싼 편, 조심",
                            f"상대 PER 백분위 {pctxt(sector_pct)} · PBR {val.get('pbr') or '—'}배", "중",
                            "고성장 지속 시 고평가가 유지될 수 있음"))
    else:
        badges.append(badge("적정 수준",
                            f"상대 PER 백분위 {pctxt(sector_pct)} · 역사적 밴드 {pctxt(hist_pct)}", "중",
                            "사이클 top에서 PER이 낮아 보이는 착시 주의"))

    peg = val.get("peg")
    if peg is not None and not trap and not expensive:
        badges.append(badge("성장 대비 무난" if peg <= 1.5 else "성장 대비 다소 비쌈",
                            f"PEG {peg}", "하", "성장률 추정이 바뀌면 PEG도 크게 변동"))

    bucket = ("저평가(밸류트랩 의심)" if trap else "저평가" if cheap
              else "고평가" if expensive else "적정가격")
    return {"metrics": metrics, "badges": badges, "bucket": bucket}
