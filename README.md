# 한눈·주식 — 한국주식 분석 판단 보조 대시보드

KOSPI/KOSDAQ 종목을 **차트·수급·회사체력·가격매력도 4축**으로 분석해,
주식을 잘 모르는 사람도 결과를 한눈에 이해하도록 **쉬운 키워드**로 번역해 보여주는
대시보드입니다.

> ⚠️ 이 앱은 **투자 자문이 아니라 판단을 돕고 감정적 매매를 줄여주는 보조 도구**입니다.
> **본 결과는 참고용이며 투자 책임은 사용자에게 있습니다.**

🔗 **데모(GitHub Pages):** https://awesomewy.github.io/

---

## 이 저장소가 GitHub Pages라는 점 (중요)

`awesomewy.github.io`는 **정적 호스팅**이라 서버(파이썬)를 상시 실행할 수 없습니다.
그래서 구조를 둘로 나눴습니다.

| 구분 | 위치 | 역할 |
|---|---|---|
| **프론트엔드(데모)** | `index.html`, `assets/`, `data/` | 정적 페이지. 백엔드가 미리 계산한 **샘플 스냅샷(JSON)** 을 표시 |
| **백엔드(참고 구현)** | `backend/` | FastAPI + pandas + `ta` + pykrx + OpenDartReader. **실데이터로 동일한 JSON**을 생성 |

핵심 규칙: **모든 수치 지표는 Python에서 계산**하고, 프론트엔드(JS)는 **계산하지 않고 표시만** 합니다.
(설계 원칙 1 — "LLM/JS 추정 금지" 준수)

---

## 설계 원칙 (전 기능 공통)

1. 모든 수치 지표는 Python(pandas, `ta`)으로 계산 — LLM/JS 추정 금지
2. 결과는 확정 가격이 아니라 **[하단~상단] 구간 + 조건부 시나리오**로 제시
3. 모든 신호에 **[근거 / 신뢰도(상·중·하) / 반대 리스크]** 병기
4. 어려운 용어는 반드시 **쉬운 키워드**로 번역 (원래 용어는 작게 부기)
5. 모든 화면 하단에 **면책 문구 + 데이터 출처 + 기준 시점** 상시 표시

## 4개 분석 축

- **축1 · 차트 흐름(기술적):** 5·20·60·120일 이동평균, RSI(14), MACD, 볼린저밴드,
  거래량 급증(20일 평균 대비 배수), 지지·저항, 20일 변동성(σ)으로 위험 등급 산출
- **축2 · 수급:** 외국인·기관 5·20일 순매수 추이 → 매집/이탈 신호
- **축3 · 회사 체력(펀더멘탈):** **성장성**(매출·영업이익·EPS 성장률, PEG)과
  **안정성**(부채·유동비율·이자보상배율, FCF, 이익의 질, 자본잠식·관리종목)을 **분리해 0~100 점수화**
  (적자기업은 PER 대신 PSR·EV/Sales, 일회성 손익 제외한 경상이익 기준)
- **축4 · 가격 매력도:** 상대(업종 PER/PBR 백분위) · 역사적(자기 3~5년 밴드 위치) ·
  성장반영(PEG) **3축 교차검증**. 저평가로 나오면 **'싼 이유' 검증 → 밸류트랩 경고**

## 종합 판정

성장성 × 안정성 × 가격매력도를 조합해 신호등(🟢 관심 / 🟡 중립 / 🔴 주의)과
위험 등급(낮음/보통/높음)을 산출합니다. **차트 신호와 펀더멘탈이 충돌하면 양쪽을 모두 표시**하고
판단은 사용자에게 위임합니다.

---

## 로컬에서 데모 보기 (정적)

```bash
python3 -m http.server 8000
# http://localhost:8000 접속
```

## 샘플 데이터 다시 생성

```bash
python3 backend/tools/gen_samples.py   # data/*.json 재생성 (순수 파이썬, 의존성 없음)
```

## 실데이터 백엔드 실행 (참고 구현)

```bash
cd backend
pip install -r requirements.txt
export DART_API_KEY=<DART OpenAPI 인증키>
uvicorn app.main:app --reload
# GET http://localhost:8000/api/analyze?code=005930
```

그런 다음 `assets/app.js` 상단의 `API()` 를 정적 스냅샷 경로 대신
백엔드 엔드포인트(`/api/analyze?code=...`)로 바꾸면 실데이터로 동작합니다.

> pykrx / OpenDartReader / 증권사 오픈API의 함수 시그니처·컬럼명·이용 약관은
> **최신 공식 문서 기준으로 반드시 재확인**하세요. `backend/` 코드는 구조를 보여주는
> 참고 구현이며, 실제 응답 스키마에 맞춰 조정이 필요합니다.

## 기술 스택

- 데이터: pykrx(KRX 시세·수급), OpenDartReader(DART 재무)
- 백엔드: Python · FastAPI · pandas · `ta`
- 프론트: 정적 HTML/CSS/JS(의존성 0) + Canvas 캔들차트 (라이트/다크 자동)

## 폴더 구조

```
.
├── index.html            # 데모 진입점 (GitHub Pages)
├── assets/               # styles.css · chart.js · app.js
├── data/                 # 백엔드 출력 스냅샷 (index.json, <code>.json)
├── backend/
│   ├── app/              # FastAPI + 4축 계산 + 종합 판정 + 스키마
│   ├── tools/gen_samples.py   # 샘플 스냅샷 생성기
│   └── requirements.txt
├── DESIGN.md             # 사양 → 구현 매핑 문서
└── .nojekyll
```

자세한 설계·구현 매핑은 [DESIGN.md](DESIGN.md) 참고.

---

_본 결과는 참고용이며 투자 책임은 사용자에게 있습니다._
