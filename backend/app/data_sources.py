"""외부 데이터 소스 어댑터 (KRX 시세·수급, DART 재무).

주의:
  - pykrx / OpenDartReader 의 정확한 함수 시그니처·컬럼명·이용 약관은
    각 라이브러리와 KRX·DART 공식 문서에서 '최신' 기준으로 반드시 재확인할 것.
    (여기 코드는 구조를 보여주는 참고 구현이며, 배포 전 실제 응답 스키마에 맞춰 조정 필요.)
  - DART API 키는 환경변수 DART_API_KEY 로 주입한다.
  - 네트워크 실패·상장폐지·신규상장 등 예외는 상위(analyze.py)에서 처리.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd


def _yyyymmdd(d: datetime) -> str:
    return d.strftime("%Y%m%d")


def fetch_ohlcv(code: str, days: int = 260) -> pd.DataFrame:
    """일봉 OHLCV. index=날짜, columns=[open, high, low, close, volume]."""
    from pykrx import stock

    end = datetime.today()
    start = end - timedelta(days=int(days * 1.6))  # 휴장일 감안 여유
    df = stock.get_market_ohlcv(_yyyymmdd(start), _yyyymmdd(end), code)
    df = df.rename(columns={
        "시가": "open", "고가": "high", "저가": "low",
        "종가": "close", "거래량": "volume",
    })
    return df[["open", "high", "low", "close", "volume"]].dropna()


def fetch_investor_flow(code: str, days: int = 30) -> pd.DataFrame:
    """투자자별 순매수 수량. columns 에 최소 '외국인', '기관합계' 포함."""
    from pykrx import stock

    end = datetime.today()
    start = end - timedelta(days=int(days * 1.8))
    df = stock.get_market_trading_value_by_date(
        _yyyymmdd(start), _yyyymmdd(end), code
    )
    # 라이브러리 버전에 따라 컬럼명이 다를 수 있어 방어적으로 매핑
    return df


def fetch_market_and_sector(code: str) -> tuple[str, str, str]:
    """(종목명, 시장(KOSPI/KOSDAQ), 업종) 반환."""
    from pykrx import stock

    name = stock.get_market_ticker_name(code)
    market = "KOSDAQ" if code in set(stock.get_market_ticker_list(market="KOSDAQ")) else "KOSPI"
    # 업종(섹터)은 KRX 업종분류 또는 별도 매핑 테이블 사용 권장
    sector = _sector_lookup(code)
    return name, market, sector


def _sector_lookup(code: str) -> str:
    # 실서비스: KRX 업종분류/제공 데이터로 대체. 여기선 자리표시자.
    return os.environ.get("SECTOR_HINT", "기타")


def fetch_financials(code: str) -> dict:
    """DART 재무제표 요약.

    반환 dict 예시 키:
      revenue[list], operating_income[list], net_income[list], eps[list],
      debt_ratio, current_ratio, interest_coverage, ocf, fcf, equity,
      is_loss(적자여부), is_capital_impaired, is_watch_issue
    실제 구현은 OpenDartReader 로 최근 3~5개년 + 최근 분기 재무를 조회해 채운다.
    일회성 손익은 제외(경상이익 기준)하고, 적자기업은 PER 대신 PSR/EV-Sales 로.
    """
    reader = _dart_reader()
    # 구현부: reader.finstate(code, year) 등으로 다개년 수집 후 정규화.
    # 본 참고 구현에서는 상위 호출부가 없을 때 안전하게 빈 구조를 돌려준다.
    raise NotImplementedError(
        "DART 재무 수집은 배포 환경에서 OpenDartReader 로 구현하세요. "
        "구조는 docstring 및 axis3_fundamental.py 의 입력 규격 참고."
    )


def _dart_reader():
    import OpenDartReader

    key = os.environ.get("DART_API_KEY")
    if not key:
        raise RuntimeError("환경변수 DART_API_KEY 가 필요합니다 (DART OpenAPI 인증키).")
    return OpenDartReader.OpenDartReader(key)
