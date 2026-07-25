"""
샘플 분석 데이터 생성기 (Pure Python, 외부 의존성 없음)
------------------------------------------------------------------
목적:
  - GitHub Pages(정적 호스팅)에는 파이썬 백엔드를 띄울 수 없으므로,
    프론트엔드 데모가 소비할 "백엔드 출력 스냅샷"(JSON)을 미리 만들어 둔다.
  - 모든 수치 지표(이동평균·RSI·MACD·볼린저·변동성 등)는 여기 Python에서
    계산한다. 프론트엔드(JS)는 계산하지 않고 '표시'만 한다.
    => 설계 원칙 1 "모든 수치 지표는 Python으로 계산, LLM/JS 추정 금지" 준수.

주의:
  - 아래 종목/수치는 UI 데모용 '합성(synthetic) 샘플'이며 실제 시세가 아니다.
  - 실서비스에서는 backend/app/ 의 FastAPI가 pykrx·OpenDartReader로 실데이터를
    받아 동일한 스키마(schema.py)로 이 JSON을 생성한다.
"""

import json
import math
import os
import random

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


# ----------------------------- 지표 계산 -----------------------------
def sma(values, window):
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(round(sum(values[i + 1 - window:i + 1]) / window, 2))
    return out


def rsi(values, period=14):
    """Wilder RSI(14)."""
    if len(values) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def ema(values, span):
    k = 2 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + k * (v - out[-1]))
    return out


def macd(values, fast=12, slow=26, signal=9):
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    hist = macd_line[-1] - signal_line[-1]
    return {
        "macd": round(macd_line[-1], 1),
        "signal": round(signal_line[-1], 1),
        "hist": round(hist, 1),
        "cross_up": macd_line[-1] > signal_line[-1],
    }


def bollinger(values, window=20, mult=2):
    seg = values[-window:]
    mid = sum(seg) / window
    var = sum((x - mid) ** 2 for x in seg) / window
    sd = math.sqrt(var)
    upper, lower = mid + mult * sd, mid - mult * sd
    last = values[-1]
    pctb = (last - lower) / (upper - lower) if upper != lower else 0.5
    return {
        "mid": round(mid, 1),
        "upper": round(upper, 1),
        "lower": round(lower, 1),
        "pct_b": round(pctb, 3),
    }


def daily_volatility(values, window=20):
    """최근 window일 로그수익률 표준편차 (일간 변동성 σ)."""
    seg = values[-(window + 1):]
    rets = [math.log(seg[i] / seg[i - 1]) for i in range(1, len(seg))]
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / len(rets)
    return math.sqrt(var)


def atr(ohlc, period=14):
    trs = []
    for i in range(1, len(ohlc)):
        h, l, pc = ohlc[i]["h"], ohlc[i]["l"], ohlc[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    seg = trs[-period:]
    return sum(seg) / len(seg)


def risk_grade_from_sigma(sigma):
    """일간 변동성 σ -> 위험 등급. 연율화(√252) 기준 대략 구간."""
    annual = sigma * math.sqrt(252)
    if annual < 0.25:
        return "low", "낮음"
    if annual < 0.45:
        return "medium", "보통"
    return "high", "높음"


# --------------------------- OHLCV 합성 ---------------------------
def synth_ohlcv(seed, start_price, n=160, drift=0.0006, vol=0.018,
                late_pump=0.0, base_volume=12_000_000):
    """재현 가능한 합성 일봉 시계열. late_pump>0 이면 최근 구간 상승 가속(과열 연출)."""
    rng = random.Random(seed)
    close = start_price
    rows = []
    from datetime import date, timedelta
    d = date(2026, 7, 24) - timedelta(days=int(n * 1.45))
    for i in range(n):
        # 주말 건너뛰기
        while d.weekday() >= 5:
            d += timedelta(days=1)
        extra = late_pump if i > n - 22 else 0.0
        ret = rng.gauss(drift + extra, vol)
        prev = close
        close = max(1.0, close * (1 + ret))
        o = prev * (1 + rng.gauss(0, vol / 3))
        h = max(o, close) * (1 + abs(rng.gauss(0, vol / 2)))
        l = min(o, close) * (1 - abs(rng.gauss(0, vol / 2)))
        vmul = 1 + abs(rng.gauss(0, 0.35)) + (1.2 if i > n - 6 and late_pump > 0 else 0)
        rows.append({
            "d": d.isoformat(),
            "o": round(o), "h": round(h), "l": round(l), "c": round(close),
            "v": int(base_volume * vmul),
        })
        d += timedelta(days=1)
    return rows


def technical_axis(ohlcv):
    closes = [r["c"] for r in ohlcv]
    vols = [r["v"] for r in ohlcv]
    ma = {w: sma(closes, w) for w in (5, 20, 60, 120)}
    last = closes[-1]
    _rsi = rsi(closes)
    _macd = macd(closes)
    _bb = bollinger(closes)
    vol20 = sum(vols[-20:]) / 20
    vol_ratio = round(vols[-1] / vol20, 2)
    sigma = daily_volatility(closes)
    _atr = atr(ohlcv)
    support = round(min(closes[-20:]))
    resistance = round(max(closes[-40:]))
    return {
        "last": last, "ma": ma, "rsi14": _rsi, "macd": _macd, "bbands": _bb,
        "vol_ratio": vol_ratio, "sigma": sigma, "atr": _atr,
        "support": support, "resistance": resistance,
    }, ma


def badge(key, raw, confidence, counter_risk):
    return {"key": key, "raw": raw, "confidence": confidence, "counter_risk": counter_risk}


def build_technical_badges(t):
    b = []
    ma5, ma20 = t["ma"][5][-1], t["ma"][20][-1]
    if ma5 and ma20:
        if ma5 > ma20:
            b.append(badge("상승 흐름 시작", "골든크로스(5일선>20일선)", "중",
                           "거래량이 함께 늘지 않으면 되돌림 가능"))
        else:
            b.append(badge("흐름 꺾임", "데드크로스(5일선<20일선)", "중",
                           "단기 저점에서 반등 나올 수 있음"))
    if t["rsi14"] is not None:
        if t["rsi14"] >= 70:
            b.append(badge("너무 많이 올랐어요, 단기과열", f"RSI {t['rsi14']} (과열)", "중",
                           "강세장에선 과열이 더 이어지기도 함"))
        elif t["rsi14"] <= 30:
            b.append(badge("바닥 다지는 중", f"RSI {t['rsi14']} (과매도)", "중",
                           "추세 하락이면 과매도가 길어질 수 있음"))
        else:
            b.append(badge("보통 흐름", f"RSI {t['rsi14']} (중립)", "하",
                           "방향성 약함 — 단독 판단 금지"))
    if t["macd"]["cross_up"]:
        b.append(badge("힘이 붙는 중", "MACD 시그널 상향", "하",
                       "0선 아래면 신뢰도 낮음"))
    else:
        b.append(badge("힘이 빠지는 중", "MACD 시그널 하향", "하",
                       "0선 위면 눌림일 수 있음"))
    if t["vol_ratio"] >= 1.6:
        b.append(badge("거래 폭발", f"거래량 20일평균 대비 {t['vol_ratio']}배", "중",
                       "급등 후 거래폭발은 고점 신호일 수도"))
    if t["bbands"]["pct_b"] >= 0.95:
        b.append(badge("밴드 상단 과열", "볼린저 상단 이탈", "하", "밴드 워킹 가능"))
    elif t["bbands"]["pct_b"] <= 0.05:
        b.append(badge("밴드 하단 눌림", "볼린저 하단 이탈", "하", "추세 하락 지속 주의"))
    return b


def make_ranges(t, buy_lo, buy_hi, stop, tgt_lo, tgt_hi, invalidation):
    return {
        "buy_zone": [buy_lo, buy_hi],
        "stop_loss": stop,
        "target_zone": [tgt_lo, tgt_hi],
        "invalidation": invalidation,
        "basis": "지지/저항선 + 20일 변동성(ATR) 기반으로 계산한 '구간'. 확정 가격이 아님.",
    }


# ------------------------------ 종목 정의 ------------------------------
def stock_samsung():
    ohlcv = synth_ohlcv(seed=42, start_price=66000, drift=0.0007, vol=0.016,
                        late_pump=0.004, base_volume=14_000_000)
    t, ma = technical_axis(ohlcv)
    last = t["last"]
    rg, rg_ko = risk_grade_from_sigma(t["sigma"])
    return {
        "meta": {
            "code": "005930", "name": "삼성전자", "market": "KOSPI",
            "sector": "반도체", "as_of": ohlcv[-1]["d"],
            "generated_at": "2026-07-25T09:05:00+09:00", "currency": "KRW",
            "price": last, "sources": ["KRX 시세(pykrx)", "DART 재무(OpenDartReader)"],
            "is_sample": True,
        },
        "verdict": {
            "signal": "neutral", "signal_label": "중립", "signal_emoji": "🟡",
            "risk_grade": rg, "risk_label": rg_ko,
            "one_liner": "회사 체력은 튼튼한데, 단기적으로 조금 올라 있어요. 눌림을 기다려도 좋아요.",
            "combo": "중성장 + 고안정 + 적정가격",
            "confidence": "중",
            "conflict": {
                "exists": True,
                "note": "차트는 '단기 과열' 신호, 펀더멘탈은 '견조'. 서로 다르게 말하는 중 — 최종 판단은 사용자 몫.",
            },
        },
        "ranges": make_ranges(
            t, buy_lo=round(t["support"]), buy_hi=round(t["ma"][20][-1]),
            stop=round(t["ma"][60][-1]),
            tgt_lo=round(t["resistance"]),
            tgt_hi=round(t["resistance"] * 1.10),
            invalidation=[
                "외국인이 3거래일 연속 순매도로 전환하면 → 수급 근거 약화",
                f"종가가 {round(t['ma'][60][-1]):,}원(60일선) 아래로 마감하면 → 추세 훼손",
            ],
        ),
        "axes": {
            "technical": {"metrics": t, "badges": build_technical_badges(t)},
            "flow": {
                "metrics": {"foreign_5d": 320_000, "foreign_20d": 1_450_000,
                            "inst_5d": -90_000, "inst_20d": 220_000},
                "badges": [
                    badge("외국인이 사 모으는 중", "외국인 20일 누적 순매수 +145만주", "중",
                          "지수 리밸런싱 등 일시적 매수일 수 있음"),
                    badge("기관은 관망", "기관 5일 소폭 순매도", "하",
                          "규모 작아 방향성으로 보기 어려움"),
                ],
            },
            "growth": {
                "score": 61,
                "metrics": {"rev_cagr_3y": 0.08, "op_growth_yoy": 0.14,
                            "op_margin_trend": "개선", "eps_growth_yoy": 0.11,
                            "peg": 1.4, "basis": "경상이익 기준, 일회성 제외"},
                "badges": [
                    badge("꾸준히 크는 회사", "매출 3년 연평균 +8%, 영업이익률 개선", "중",
                          "업황(반도체 사이클) 둔화 시 성장 흔들릴 수 있음"),
                ],
            },
            "stability": {
                "score": 86,
                "metrics": {"debt_ratio": 0.32, "current_ratio": 2.6,
                            "interest_coverage": 41.0, "fcf_positive": True,
                            "ocf_vs_ni": 1.18, "capital_impairment": False,
                            "watch_issue": False},
                "badges": [
                    badge("재무 튼튼", "부채비율 32% · 유동비율 260%", "상",
                          "대규모 설비투자 시 현금흐름 변동 가능"),
                    badge("이익의 질 좋음", "영업현금흐름이 순이익보다 큼(1.18배)", "상",
                          "일시적 운전자본 효과일 수 있어 추세 확인 필요"),
                ],
            },
            "valuation": {
                "metrics": {"per": 13.5, "pbr": 1.3, "peg": 1.4,
                            "sector_per_pct": 45, "hist_per_pct": 52,
                            "method": "PER/PBR (흑자기업)",
                            "value_trap": {"suspected": False, "reason": None}},
                "badges": [
                    badge("적정 수준", "업종 PER 백분위 45% · 역사적 밴드 중간(52%)", "중",
                          "반도체는 사이클 top에서 PER이 낮아 보이는 착시 주의"),
                    badge("성장 대비 무난", "PEG 1.4 (성장 반영 시 과하지 않음)", "하",
                          "성장률 추정이 바뀌면 PEG도 크게 변동"),
                ],
            },
        },
        "chart": {"ohlcv": ohlcv, "ma": {str(w): ma[w] for w in (5, 20, 60, 120)}},
        "disclaimer": "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다.",
    }


def stock_growth():
    ohlcv = synth_ohlcv(seed=7, start_price=180000, drift=0.0012, vol=0.032,
                        late_pump=0.006, base_volume=1_800_000)
    t, ma = technical_axis(ohlcv)
    last = t["last"]
    rg, rg_ko = risk_grade_from_sigma(t["sigma"])
    return {
        "meta": {
            "code": "247540", "name": "에코프로비엠", "market": "KOSDAQ",
            "sector": "2차전지 소재", "as_of": ohlcv[-1]["d"],
            "generated_at": "2026-07-25T09:05:00+09:00", "currency": "KRW",
            "price": last, "sources": ["KRX 시세(pykrx)", "DART 재무(OpenDartReader)"],
            "is_sample": True,
        },
        "verdict": {
            "signal": "watch", "signal_label": "관심", "signal_emoji": "🟢",
            "risk_grade": rg, "risk_label": rg_ko,
            "one_liner": "빠르게 크는 회사예요. 다만 가격이 성장 기대를 이미 많이 반영했고 변동성이 큽니다.",
            "combo": "고성장 + 중안정 + 고평가(성장 프리미엄)",
            "confidence": "중",
            "conflict": {"exists": False, "note": "차트·수급·성장이 같은 방향(강세)을 가리킴. 단, 가격 부담이 리스크."},
        },
        "ranges": make_ranges(
            t, buy_lo=round(t["ma"][20][-1]), buy_hi=round(t["ma"][5][-1]),
            stop=round(t["ma"][60][-1]),
            tgt_lo=round(t["resistance"]),
            tgt_hi=round(t["resistance"] * 1.15),
            invalidation=[
                "외국인·기관이 동시에 순매도로 전환하면 → 수급 주도 상승 종료 신호",
                "다음 분기 매출 성장률이 두 자릿수 아래로 꺾이면 → 고밸류 정당화 약화",
            ],
        ),
        "axes": {
            "technical": {"metrics": t, "badges": build_technical_badges(t)},
            "flow": {
                "metrics": {"foreign_5d": 210_000, "foreign_20d": 780_000,
                            "inst_5d": 55_000, "inst_20d": 190_000},
                "badges": [
                    badge("외국인이 사 모으는 중", "외국인 20일 누적 +78만주", "중",
                          "고변동 종목이라 하루 만에 되돌릴 수 있음"),
                    badge("기관도 동참", "기관 20일 순매수 +19만주", "중", "차익실현 물량 유입 가능"),
                ],
            },
            "growth": {
                "score": 88,
                "metrics": {"rev_cagr_3y": 0.41, "op_growth_yoy": 0.35,
                            "op_margin_trend": "정체", "eps_growth_yoy": 0.30,
                            "peg": 2.1, "basis": "경상이익 기준"},
                "badges": [
                    badge("쑥쑥 크는 회사", "매출 3년 연평균 +41%", "상",
                          "전방(전기차) 수요 둔화 시 성장률 급감 위험"),
                    badge("성장 대비 비쌈", "PEG 2.1 (성장보다 가격이 앞섬)", "중",
                          "성장 가속되면 PEG 정당화될 수도"),
                ],
            },
            "stability": {
                "score": 58,
                "metrics": {"debt_ratio": 1.35, "current_ratio": 1.1,
                            "interest_coverage": 4.2, "fcf_positive": False,
                            "ocf_vs_ni": 0.7, "capital_impairment": False,
                            "watch_issue": False},
                "badges": [
                    badge("빚 부담 큼, 주의", "부채비율 135% · 이자보상배율 4.2배", "중",
                          "증설 투자 성격 — 성장기 부채는 무조건 나쁘진 않음"),
                    badge("현금 나가는 중(투자기)", "잉여현금흐름(FCF) 마이너스", "중",
                          "설비투자 마무리되면 개선 가능"),
                ],
            },
            "valuation": {
                "metrics": {"per": 48.0, "pbr": 6.8, "peg": 2.1,
                            "sector_per_pct": 78, "hist_per_pct": 60,
                            "method": "PER/PBR + PEG (성장주)",
                            "value_trap": {"suspected": False, "reason": None}},
                "badges": [
                    badge("비싼 편, 조심", "업종 PER 백분위 78% · PBR 6.8배", "중",
                          "고성장 지속 시 고평가가 유지될 수 있음"),
                ],
            },
        },
        "chart": {"ohlcv": ohlcv, "ma": {str(w): ma[w] for w in (5, 20, 60, 120)}},
        "disclaimer": "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다.",
    }


def stock_valuetrap():
    ohlcv = synth_ohlcv(seed=99, start_price=42000, drift=-0.0011, vol=0.022,
                        late_pump=0.0, base_volume=900_000)
    t, ma = technical_axis(ohlcv)
    last = t["last"]
    rg, rg_ko = risk_grade_from_sigma(t["sigma"])
    return {
        "meta": {
            "code": "000000", "name": "샘플소재(가상)", "market": "KOSPI",
            "sector": "화학", "as_of": ohlcv[-1]["d"],
            "generated_at": "2026-07-25T09:05:00+09:00", "currency": "KRW",
            "price": last, "sources": ["KRX 시세(pykrx)", "DART 재무(OpenDartReader)"],
            "is_sample": True,
        },
        "verdict": {
            "signal": "caution", "signal_label": "주의", "signal_emoji": "🔴",
            "risk_grade": rg, "risk_label": rg_ko,
            "one_liner": "PER만 보면 싸 보이지만, 실적이 꺾이는 중이라 '싼 데는 이유'가 있어 보여요.",
            "combo": "저성장(역성장) + 중안정 + 저평가(밸류트랩 의심)",
            "confidence": "중",
            "conflict": {"exists": True,
                         "note": "밸류에이션은 '싸다'고 하지만 성장·차트는 '약하다'. 저가 매수 함정(value trap) 경계."},
        },
        "ranges": make_ranges(
            t, buy_lo=round(t["support"] * 0.97), buy_hi=round(t["support"]),
            stop=round(t["support"] * 0.92),
            tgt_lo=round(t["ma"][60][-1]),
            tgt_hi=round(t["ma"][120][-1]) if t["ma"][120][-1] else round(t["resistance"]),
            invalidation=[
                "분기 영업이익이 흑자 전환하고 매출이 반등하면 → 밸류트랩 판단 해제",
                "외국인이 5일 연속 순매수로 돌아서면 → 바닥 신뢰도 상승",
            ],
        ),
        "axes": {
            "technical": {"metrics": t, "badges": build_technical_badges(t)},
            "flow": {
                "metrics": {"foreign_5d": -140_000, "foreign_20d": -620_000,
                            "inst_5d": -80_000, "inst_20d": -310_000},
                "badges": [
                    badge("외국인 이탈 주의", "외국인 20일 누적 -62만주", "중",
                          "낙폭 과대 반등 시 단기 매수 유입 가능"),
                    badge("기관도 파는 중", "기관 20일 순매도 -31만주", "중", "저점 매집 초입일 가능성은 낮음"),
                ],
            },
            "growth": {
                "score": 24,
                "metrics": {"rev_cagr_3y": -0.06, "op_growth_yoy": -0.38,
                            "op_margin_trend": "악화", "eps_growth_yoy": -0.45,
                            "peg": None, "basis": "성장률 음수 → PEG 적용 불가"},
                "badges": [
                    badge("성장 멈춤(역성장)", "매출 3년 연평균 -6%, 영업이익 급감", "중",
                          "업황 바닥에서 턴어라운드 가능성은 별도 점검 필요"),
                    badge("PEG 적용 불가", "성장률이 음수라 PEG 계산 의미 없음", "상",
                          "성장 회복 시 재평가 대상"),
                ],
            },
            "stability": {
                "score": 55,
                "metrics": {"debt_ratio": 0.78, "current_ratio": 1.4,
                            "interest_coverage": 2.1, "fcf_positive": True,
                            "ocf_vs_ni": 1.4, "capital_impairment": False,
                            "watch_issue": False},
                "badges": [
                    badge("당장 위험은 아님", "부채비율 78% · 유동비율 140%", "중",
                          "이익 감소가 지속되면 이자 부담 커질 수 있음"),
                ],
            },
            "valuation": {
                "metrics": {"per": 5.2, "pbr": 0.4, "peg": None,
                            "sector_per_pct": 8, "hist_per_pct": 12,
                            "method": "PER/PBR (흑자지만 감익) · PSR 병행",
                            "value_trap": {"suspected": True,
                                           "reason": "PER·PBR은 하위권(싸다)이나 이익이 감소 추세 — 저평가가 아니라 '실적 악화 반영'일 가능성"}},
                "badges": [
                    badge("싸지만 이유 있음", "PER 5.2 · PBR 0.4 (밸류트랩 의심)", "중",
                          "업황 반등·구조조정 성공 시 진짜 저평가일 수 있음"),
                ],
            },
        },
        "chart": {"ohlcv": ohlcv, "ma": {str(w): ma[w] for w in (5, 20, 60, 120)}},
        "disclaimer": "본 결과는 참고용이며 투자 책임은 사용자에게 있습니다.",
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    stocks = {
        "005930": stock_samsung(),
        "247540": stock_growth(),
        "000000": stock_valuetrap(),
    }
    index = []
    for code, data in stocks.items():
        path = os.path.join(OUT_DIR, f"{code}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        index.append({
            "code": code, "name": data["meta"]["name"],
            "market": data["meta"]["market"], "sector": data["meta"]["sector"],
            "signal": data["verdict"]["signal"], "combo": data["verdict"]["combo"],
        })
        print("wrote", path)
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"stocks": index}, f, ensure_ascii=False, indent=2)
    print("wrote index.json")


if __name__ == "__main__":
    main()
