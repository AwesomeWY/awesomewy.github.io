# 설계 문서 — 사양 → 구현 매핑

이 문서는 요구 사양을 어디에서 어떻게 구현했는지 대응시킵니다.
검증 관점: **"수치는 Python, 표시는 JS"** 경계가 지켜졌는지가 핵심입니다.

## 데이터 계약 (백엔드 ↔ 프론트)

한 종목 분석 결과는 하나의 JSON 객체(`schema.AnalysisResult`)입니다.

```
meta      종목/시장/업종/기준시점/생성시각/출처/샘플여부
verdict   신호등·위험등급·한줄요약·조합·신뢰도·충돌표시
ranges    매수구간·손절·목표구간·판단변경조건·산출근거
axes      technical / flow / growth / stability / valuation
chart     ohlcv[] + ma{5,20,60,120}
disclaimer 면책 문구
```

- 실서비스: `GET /api/analyze?code=` → 위 JSON (`backend/app/main.py`)
- 정적 데모: `data/<code>.json` 스냅샷 (`backend/tools/gen_samples.py` 생성)
- 프론트: `assets/app.js` 가 위 JSON을 **표시만** 함

## 절대 설계 원칙 대응

| 원칙 | 구현 위치 |
|---|---|
| 1. 수치는 Python 계산, LLM/JS 추정 금지 | `backend/app/indicators.py`(ta/pandas), 각 `axisN_*.py`. 프론트 `app.js`·`chart.js`는 계산 없음 |
| 2. 확정가 아닌 [하단~상단] 구간 + 시나리오 | `scoring.ranges()` → `ranges.buy_zone/target_zone/invalidation` |
| 3. 신호마다 [근거/신뢰도/반대리스크] | `keywords.badge(key, raw, confidence, counter_risk)` — 모든 배지 필수 4필드 |
| 4. 어려운 용어 → 쉬운 키워드 | 각 축 `_badges()`: `key`(쉬운말) + `raw`(원래용어 부기) |
| 5. 하단 면책·출처·기준시점 상시 | `app.js` 푸터 + `meta.as_of/sources/generated_at` + `disclaimer` |

## 축별 매핑

### 축1 · 차트 흐름 — `axis1_technical.py` + `indicators.py`
- 이동평균 5·20·60·120 (`moving_averages`), RSI14(Wilder, `rsi`), MACD(`macd`),
  볼린저(`bollinger`), 거래량 배수(`volume_ratio`), 지지·저항(`support_resistance`),
  20일 변동성 σ(`daily_volatility`) → 위험등급(`annualized_risk_grade`)
- 키워드: 골든/데드크로스, RSI 과열/과매도, MACD, 거래폭발, 밴드 이탈

### 축2 · 수급 — `axis2_flow.py`
- 외국인·기관 5·20일 순매수 합계 → "사 모으는 중 / 이탈 주의" 등

### 축3 · 회사 체력 — `axis3_fundamental.py` (성장/안정 **분리**)
- `growth()`: 매출 3년 CAGR·영업이익·EPS 성장률·이익률 추세·PEG → 0~100
- `stability()`: 부채·유동비율·이자보상배율·FCF·이익의 질(영업현금/순이익)·
  자본잠식·관리종목 → 0~100
- 적자기업은 PER 대신 PSR/EV-Sales (축4에서 처리), 경상이익 기준 전제

### 축4 · 가격 매력도 — `axis4_valuation.py` (3축 교차검증)
- 상대(업종 PER 백분위) · 역사적(자기 밴드 위치) · 성장반영(PEG)
- **성장률 음수 → PEG "적용 불가" 명시**
- **저평가 + 실적 악화 → 밸류트랩 경고**(`value_trap.suspected/reason`)

### 종합 판정 — `scoring.py`
- `verdict()`: 차트 편향(`_chart_bias`) + 펀더 편향(`_fundamental_bias`) → 신호등
- 밸류트랩이면 '관심' 강등, 차트·펀더 반대면 `conflict.exists=True`로 양쪽 표시
- 조합 라벨: `keywords.combo_label()` ("고성장 + 고안정 + 저평가" 등)

## 출력 UI 대응 (`index.html` + `assets/`)
- 종합 카드: 큰 신호등 1개 + 위험 등급 + 한줄 요약 + 충돌 배너
- 축별 쉬운 키워드 배지 (신뢰도 색상, 반대 리스크 병기)
- 구간: 매수/손절/목표 3박스 + "판단을 바꿀 조건" 리스트
- 차트: Canvas 캔들 + MA 4선 (한국 관행: 상승=빨강, 하락=파랑)
- 하단: 출처·기준시점·갱신시각·면책, 라이트/다크 자동

## 금지 사항 준수
- 미래 가격 확정 예측·단정 없음 → 전부 '구간 + 조건부' 표현
- 단일 지표 고·저평가 단정 금지 → 축4는 항상 3축 교차 + 밸류트랩 검증
- 면책·기준시점 없는 출력 없음 → 스키마 필수 필드 + 푸터 상시

## 데모의 한계 (정직성)
- `data/*.json`은 UI 검증용 **합성(synthetic) 샘플**이며 실제 시세가 아님(`meta.is_sample=true`).
- pykrx/OpenDartReader의 함수·컬럼·약관은 배포 전 최신 문서로 재확인 필요.
- 백엔드 `fetch_financials()`는 DART 연동 골격만 제공(환경별 구현 필요).
