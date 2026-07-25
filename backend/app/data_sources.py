"""외부 데이터 소스 어댑터 (KRX 시세·수급·펀더멘탈, DART 재무).

데이터 계층 전략 (회복력 우선):
  - KRX(pykrx): API 키 불필요. 시세·수급·PER/PBR/EPS 제공 → 축1·2·4의 기본은 항상 동작.
  - DART(OpenDartReader): DART_API_KEY 필요. 다개년 재무 → 축3(성장/안정) 심화.
    키가 없거나 파싱 실패 시 예외를 던지지 않고 None 을 돌려주어 상위(analyze.py)가
    "정보 부족" 상태로 우아하게 degrade 하도록 한다.

주의:
  - pykrx / OpenDartReader 의 함수 시그니처·컬럼명·이용 약관은 각 라이브러리와
    KRX·DART 공식 문서에서 '최신' 기준으로 재확인할 것. 버전에 따라 컬럼명이 바뀔 수 있어
    아래는 방어적으로(있으면 사용) 처리한다.
"""
from __future__ import annotations

import functools
import math
import os
from datetime import datetime, timedelta

import pandas as pd


def _ymd(d: datetime) -> str:
    return d.strftime("%Y%m%d")


def _to_int(x) -> int | None:
    """'1,234' / '-' / '' / NaN 등을 안전하게 int 로."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return None if (isinstance(x, float) and math.isnan(x)) else int(x)
    s = str(x).replace(",", "").strip()
    if s in ("", "-", "N/A"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


# ------------------------------- 종목 메타 -------------------------------
@functools.lru_cache(maxsize=4)
def _ticker_index(_bucket: str) -> dict[str, str]:
    """{종목명: 코드} 및 {코드: 시장} 인덱스. 하루 단위 캐시(bucket=날짜)."""
    from pykrx import stock

    names, markets = {}, {}
    for mkt in ("KOSPI", "KOSDAQ"):
        for code in stock.get_market_ticker_list(market=mkt):
            nm = stock.get_market_ticker_name(code)
            names[nm] = code
            markets[code] = mkt
    return {"names": names, "markets": markets}


def _index_today() -> dict:
    return _ticker_index(datetime.today().strftime("%Y%m%d"))


def resolve_code(query: str) -> str | None:
    """종목코드(6자리) 또는 종목명 → 코드. 못 찾으면 None."""
    q = (query or "").strip()
    if q.isdigit() and len(q) == 6:
        return q
    names = _index_today()["names"]
    if q in names:
        return names[q]
    # 부분 일치 (가장 짧은 이름 우선)
    hits = sorted((nm for nm in names if q and q in nm), key=len)
    return names[hits[0]] if hits else None


def fetch_market_and_sector(code: str) -> tuple[str, str, str]:
    from pykrx import stock

    name = stock.get_market_ticker_name(code)
    market = _index_today()["markets"].get(code, "KOSPI")
    sector = os.environ.get("SECTOR_HINT", "")  # 실서비스: KRX 업종분류 매핑 권장
    return name, market, sector


# -------------------------------- 시세 --------------------------------
def fetch_ohlcv(code: str, days: int = 260) -> pd.DataFrame:
    """수정주가 일봉 OHLCV. index=날짜, columns=[open,high,low,close,volume]."""
    from pykrx import stock

    end = datetime.today()
    start = end - timedelta(days=int(days * 1.7))  # 휴장일 여유
    df = stock.get_market_ohlcv(_ymd(start), _ymd(end), code, adjusted=True)
    df = df.rename(columns={"시가": "open", "고가": "high", "저가": "low",
                            "종가": "close", "거래량": "volume"})
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df = df[df["close"] > 0]
    if df.empty:
        raise ValueError(f"시세 데이터가 비었습니다 (코드 {code}). 상장폐지·신규상장 여부 확인.")
    return df


# -------------------------------- 수급 --------------------------------
def fetch_investor_flow(code: str, days: int = 30) -> pd.DataFrame:
    """투자자별 '순매수 거래대금'(원)을 날짜별로. 컬럼에 외국인/기관합계 포함(방어적)."""
    from pykrx import stock

    end = datetime.today()
    start = end - timedelta(days=int(days * 1.9))
    try:
        df = stock.get_market_trading_value_by_date(_ymd(start), _ymd(end), code)
    except Exception:
        return pd.DataFrame()
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame()


# ------------------------------ 가격 지표 ------------------------------
def _percentile_of(value: float, series: pd.Series) -> int | None:
    """series 안에서 value 의 백분위(0~100). 양수만 대상."""
    s = pd.to_numeric(series, errors="coerce")
    s = s[(s > 0) & s.notna()]
    if s.empty or value is None or value <= 0:
        return None
    return int(round((s < value).mean() * 100))


def fetch_valuation(code: str, market: str) -> dict:
    """pykrx 펀더멘탈에서 PER/PBR/EPS + 역사적 PER 밴드 위치 + 시장 상대 백분위."""
    from pykrx import stock

    end = datetime.today()
    start = end - timedelta(days=365 * 3 + 30)
    fund = stock.get_market_fundamental_by_date(_ymd(start), _ymd(end), code)
    last = fund.dropna(how="all").iloc[-1]
    per = float(last.get("PER") or 0) or None
    pbr = float(last.get("PBR") or 0) or None
    eps = _to_int(last.get("EPS"))
    is_loss = (per is None) or (eps is not None and eps <= 0)

    # 역사적 PER 밴드 내 현재 위치 (자기 자신 3년)
    hist_per_pct = _percentile_of(per, fund["PER"]) if per else None

    # 상대 백분위: 같은 시장(KOSPI/KOSDAQ) 종목들의 PER 분포 대비 (업종 매핑 없을 때의 근사)
    sector_per_pct = None
    try:
        peers = stock.get_market_fundamental_by_ticker(_ymd(end), market=market)
        sector_per_pct = _percentile_of(per, peers["PER"]) if per else None
    except Exception:
        pass

    return {
        "per": round(per, 1) if per else None,
        "pbr": round(pbr, 2) if pbr else None,
        "eps": eps,
        "is_loss": is_loss,
        "hist_per_pct": hist_per_pct,
        "sector_per_pct": sector_per_pct,
        "relative_basis": f"{market} 시장 전체 대비 근사(업종 매핑 미적용)",
    }


# ------------------------------ DART 재무 ------------------------------
_ACCOUNTS = {
    "매출액": "revenue", "영업이익": "op_income", "당기순이익": "net_income",
    "부채총계": "liabilities", "자본총계": "equity",
    "유동자산": "current_assets", "유동부채": "current_liabilities",
}


def fetch_financials(code: str) -> dict | None:
    """DART 다개년 재무 → 성장/안정 입력 dict. 키 없거나 실패 시 None(우아한 degrade)."""
    if not os.environ.get("DART_API_KEY"):
        return None
    try:
        return _fetch_financials_impl(code)
    except Exception:
        return None


def _fetch_financials_impl(code: str) -> dict | None:
    import OpenDartReader

    reader = OpenDartReader.OpenDartReader(os.environ["DART_API_KEY"])
    year = datetime.today().year - 1

    # 한 번의 finstate 호출로 당기/전기/전전기(3개년)의 주요 계정을 얻는다.
    fs = None
    for y in (year, year - 1):  # 최근 연도 미공시면 한 해 뒤로
        try:
            fs = reader.finstate(code, y)
        except Exception:
            fs = None
        if fs is not None and len(fs) > 0:
            year = y
            break
    if fs is None or len(fs) == 0:
        return None

    vals: dict[str, list[int | None]] = {}
    for _, row in fs.iterrows():
        nm = str(row.get("account_nm", "")).strip()
        key = _ACCOUNTS.get(nm)
        if not key or key in vals:
            continue
        cur = _to_int(row.get("thstrm_amount"))
        prev = _to_int(row.get("frmtrm_amount"))
        bfe = _to_int(row.get("bfefrmtrm_amount"))
        vals[key] = [bfe, prev, cur]  # [전전기, 전기, 당기]

    def cur(k):
        return vals.get(k, [None, None, None])[2]

    def prev(k):
        return vals.get(k, [None, None, None])[1]

    def bfe(k):
        return vals.get(k, [None, None, None])[0]

    # ---- 성장성 ----
    rev_cagr = _cagr(bfe("revenue"), cur("revenue"), 2)
    op_yoy = _yoy(prev("op_income"), cur("op_income"))
    ni_yoy = _yoy(prev("net_income"), cur("net_income"))  # EPS 성장 대용
    margin_trend = _margin_trend(prev("revenue"), prev("op_income"),
                                 cur("revenue"), cur("op_income"))

    # ---- 안정성 ----
    debt_ratio = _ratio(cur("liabilities"), cur("equity"))
    current_ratio = _ratio(cur("current_assets"), cur("current_liabilities"))
    equity_cur = cur("equity")
    is_capital_impaired = equity_cur is not None and equity_cur < 0

    growth = {
        "rev_cagr_3y": rev_cagr, "op_growth_yoy": op_yoy,
        "eps_growth_yoy": ni_yoy, "op_margin_trend": margin_trend,
        "peg": None,  # analyze 단계에서 PER/성장률로 산출
    }
    stability = {
        "debt_ratio": debt_ratio, "current_ratio": current_ratio,
        "interest_coverage": None,   # finstate 요약엔 없음(별도 finstate_all 필요)
        "fcf_positive": None, "ocf_vs_ni": None,  # 현금흐름표 별도 파싱 필요
        "is_capital_impaired": is_capital_impaired, "is_watch_issue": False,
    }
    return {"growth": growth, "stability": stability,
            "net_income_cur": cur("net_income"), "dart_year": year,
            "partial": True}  # 이자보상배율·현금흐름은 미포함(부분 데이터)


# ----------------------------- 재무 계산 헬퍼 -----------------------------
def _cagr(begin, end, years):
    if not begin or not end or begin <= 0 or end <= 0:
        return None
    return round((end / begin) ** (1 / years) - 1, 4)


def _yoy(prev, cur):
    if prev is None or cur is None or prev == 0:
        return None
    return round(cur / abs(prev) - 1, 4) if prev > 0 else None


def _ratio(a, b):
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 4)


def _margin_trend(rev_prev, op_prev, rev_cur, op_cur):
    if not rev_prev or not rev_cur:
        return "정보 부족"
    mp = (op_prev or 0) / rev_prev
    mc = (op_cur or 0) / rev_cur
    if mc - mp > 0.005:
        return "개선"
    if mc - mp < -0.005:
        return "악화"
    return "정체"
