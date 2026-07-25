# 한눈·주식 백엔드 — 실시간 분석 API

KRX(pykrx)·DART(OpenDartReader) 데이터를 받아 4축 분석 결과(JSON)를 돌려주는
FastAPI 서버입니다. GitHub Pages(정적)와 **별개**로 배포하며, 프론트에서 이 서버 주소를
지정하면 종목명/코드로 **실시간 조회**가 됩니다.

## 데이터 계층 (중요)

| 축 | 소스 | API 키 | 키 없을 때 |
|---|---|---|---|
| 축1 차트 · 축2 수급 · 축4 가격(PER/PBR) | KRX (pykrx) | **불필요** | 정상 동작 |
| 축3 성장성·안정성 | DART (OpenDartReader) | `DART_API_KEY` 필요 | "재무 정보 없음"으로 우아하게 degrade |

즉 **키 없이도 차트·수급·가격 분석은 바로 작동**하고, DART 키를 넣으면 재무(성장/안정)까지 채워집니다.

## 엔드포인트

```
GET /healthz                        → {"ok": true, "dart": false}
GET /api/resolve?query=삼성전자      → {"code":"005930","name":"삼성전자","market":"KOSPI"}
GET /api/analyze?query=삼성전자      → 분석 결과(JSON, schema.AnalysisResult)
GET /api/analyze?code=005930        → 위와 동일 (코드 직접 지정)
```

## 로컬 실행

```bash
cd backend
pip install -r requirements.txt
export DART_API_KEY=<DART OpenAPI 인증키>   # (선택) https://opendart.fss.or.kr 발급
uvicorn app.main:app --reload --port 8000
# 확인: curl "http://localhost:8000/api/analyze?query=삼성전자"
```

또는 Docker:

```bash
cd backend
docker build -t hannun-stock-api .
docker run -p 8000:8000 -e DART_API_KEY=<키> hannun-stock-api
```

---

## 무료 배포 (택1)

### A. Render (가장 쉬움 — 이 저장소에 블루프린트 포함)

1. https://render.com 가입 → **New + → Blueprint**
2. 이 GitHub 저장소 선택 → 루트의 [`render.yaml`](../render.yaml) 자동 감지
3. (선택) `DART_API_KEY` 환경변수 입력 → **Apply**
4. 배포되면 주소가 나옵니다: `https://hannun-stock-api.onrender.com`
   - 확인: 위 주소 + `/healthz`

> 무료 플랜은 15분 미사용 시 잠들어 **첫 요청이 30~60초** 걸릴 수 있습니다(콜드 스타트).

### B. Railway

1. https://railway.app → **New Project → Deploy from GitHub repo**
2. Root Directory를 `backend` 로 지정 (Dockerfile 자동 사용, [`railway.json`](railway.json) 포함)
3. Variables 에 `DART_API_KEY` 추가 → 배포 → 공개 도메인 생성(Settings → Networking)

### C. Fly.io / 자체 서버

`backend/Dockerfile` 로 어디서나 실행됩니다.
`fly launch` 후 `fly secrets set DART_API_KEY=...` 로 키를 넣으세요.

---

## 프론트(GitHub Pages)와 연결

배포로 받은 주소를 프론트에 알려주는 방법 **3가지 중 하나**:

1. **버튼** — 데모 페이지 우측 상단 **"백엔드 연결"** → 주소 붙여넣기 (브라우저에 저장)
2. **URL** — `https://awesomewy.github.io/?api=https://hannun-stock-api.onrender.com`
3. **코드 고정** — [`assets/config.js`](../assets/config.js) 의 `STOCK_API_BASE` 에 주소 입력 후 커밋

연결되면 배지가 **🟢 실시간**으로 바뀌고, 종목명/코드로 실시간 조회가 됩니다.
연결을 끊으려면 "백엔드 연결"에서 빈칸을 저장하면 데모 모드로 돌아갑니다.

> CORS: 기본은 전체 허용(`ALLOW_ORIGINS=*`). 배포 도메인만 허용하려면
> `ALLOW_ORIGINS=https://awesomewy.github.io` 로 설정하세요.

---

## 구현 상태 / 한계 (정직 고지)

- **검증됨:** 4축 계산 로직, 종합 판정, None-safe/적자/밸류트랩 처리(단위 테스트 통과),
  pykrx 함수 시그니처, 프론트 실시간 연동(스텁 백엔드로 E2E 확인).
- **배포 환경에서 확인 필요:** 이 개발 샌드박스는 외부망(KRX)이 차단돼 **실 KRX/DART 호출은
  배포 후 검증**해야 합니다. pykrx/OpenDartReader의 컬럼명·약관은 버전에 따라 달라질 수 있어
  방어적으로 파싱하지만, 배포 후 실제 응답으로 한 번 확인하세요.
- **부분 데이터:** DART 요약 재무(`finstate`)에는 **이자보상배율·현금흐름(FCF/영업현금)** 이
  없어 해당 항목은 "정보 부족"으로 표시됩니다. 정밀화하려면 `finstate_all`(현금흐름표)
  파싱을 `data_sources.fetch_financials` 에 추가하세요.
- **업종 백분위:** 업종 매핑 테이블이 없어 상대 PER 백분위는 **시장(KOSPI/KOSDAQ) 전체 대비
  근사**로 계산하며 배지에 그 사실을 표기합니다. 업종 매핑을 넣으면 사양대로 '동종업계'가 됩니다.

이 앱은 투자 자문이 아니라 판단 보조 도구입니다.
**본 결과는 참고용이며 투자 책임은 사용자에게 있습니다.**
