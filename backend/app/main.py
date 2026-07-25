"""FastAPI 진입점.

실행:
  export DART_API_KEY=... ; uvicorn app.main:app --reload
엔드포인트:
  GET /api/analyze?code=005930  -> 분석 결과(JSON, schema.AnalysisResult)
  GET /healthz

프론트엔드(assets/app.js)의 API() 를 이 엔드포인트로 바꾸면 실데이터로 동작한다.
정적 GitHub Pages 데모에서는 미리 생성한 data/*.json 스냅샷을 사용한다.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import analyze as analyzer
from .schema import AnalysisResult

app = FastAPI(title="한눈·주식 분석 API", version="0.1.0")

# 데모/개발용 CORS. 배포 시 허용 도메인을 좁힐 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/analyze", response_model=AnalysisResult)
def analyze(code: str):
    code = code.strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "종목코드는 6자리 숫자여야 합니다 (예: 005930).")
    try:
        return analyzer.analyze(code)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"데이터 수집/분석 실패: {e}")
