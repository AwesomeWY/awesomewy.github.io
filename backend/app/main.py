"""FastAPI 진입점.

실행:
  export DART_API_KEY=...        # (선택) 있으면 재무 분석(축3)까지, 없으면 축1·2·4만
  uvicorn app.main:app --host 0.0.0.0 --port 8000

엔드포인트:
  GET /healthz
  GET /api/resolve?query=삼성전자         -> {"code": "005930", "name": "삼성전자"}
  GET /api/analyze?query=삼성전자 (또는 code=005930) -> 분석 결과(JSON)

프론트엔드(assets/app.js)에서 window.STOCK_API_BASE 를 이 서버 주소로 지정하면
정적 스냅샷 대신 실데이터로 동작한다.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import analyze as analyzer
from . import data_sources
from .schema import AnalysisResult

app = FastAPI(title="한눈·주식 분석 API", version="0.2.0")

# CORS: 기본은 전체 허용(데모). 배포 시 ALLOW_ORIGINS(콤마 구분)로 좁힐 것.
_origins = os.environ.get("ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_methods=["GET"], allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "dart": bool(os.environ.get("DART_API_KEY"))}


@app.get("/api/resolve")
def resolve(query: str = Query(..., description="종목명 또는 6자리 코드")):
    try:
        code = data_sources.resolve_code(query)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"종목 조회 실패: {e}")
    if not code:
        raise HTTPException(404, f"‘{query}’ 에 해당하는 종목을 찾지 못했습니다.")
    name, market, _ = data_sources.fetch_market_and_sector(code)
    return {"code": code, "name": name, "market": market}


@app.get("/api/analyze", response_model=AnalysisResult)
def analyze(
    code: str | None = None,
    query: str | None = Query(None, description="종목명 또는 코드 (code 대신 사용 가능)"),
):
    raw = (code or query or "").strip()
    if not raw:
        raise HTTPException(400, "code 또는 query 파라미터가 필요합니다.")
    try:
        resolved = data_sources.resolve_code(raw)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"종목 조회 실패: {e}")
    if not resolved:
        raise HTTPException(404, f"‘{raw}’ 종목을 찾지 못했습니다. 종목명 철자나 6자리 코드를 확인하세요.")
    try:
        return analyzer.analyze(resolved)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"데이터 수집/분석 실패: {e}")
