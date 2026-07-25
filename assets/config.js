/*
 * config.js — 데이터 소스 설정
 *
 * 기본값은 빈 문자열("") = 데모 모드(정적 data/*.json 사용).
 * 배포한 백엔드에 연결하는 방법 3가지:
 *   1) 아래 STOCK_API_BASE 에 직접 URL 입력 후 커밋
 *   2) 화면의 "백엔드 연결" 버튼으로 URL 입력 (브라우저에 저장됨)
 *   3) 주소 뒤에 ?api=https://내백엔드주소  를 붙여 접속 (?api= 만 붙이면 해제)
 */
window.STOCK_API_BASE = ""; // 예: "https://hannun-stock-api.onrender.com"

window.HannunConfig = (function () {
  const LS_KEY = "stockApiBase";
  const clean = u => (u || "").trim().replace(/\/+$/, "");

  // URL 쿼리(?api=)가 있으면 저장/해제
  try {
    const p = new URL(location.href).searchParams;
    if (p.has("api")) {
      const v = clean(p.get("api"));
      if (v) localStorage.setItem(LS_KEY, v);
      else localStorage.removeItem(LS_KEY);
    }
  } catch (_) {}

  function get() {
    return clean(window.STOCK_API_BASE) || clean(localStorage.getItem(LS_KEY));
  }
  function set(v) {
    const c = clean(v);
    if (c) localStorage.setItem(LS_KEY, c);
    else localStorage.removeItem(LS_KEY);
  }
  return { get, set };
})();
