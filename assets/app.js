/*
 * app.js — 대시보드 렌더러
 * 역할: 백엔드(Python/FastAPI)가 만든 분석 JSON을 받아 '표시'만 한다.
 *       모든 수치 지표·점수·키워드 번역은 백엔드에서 계산된 상태로 들어온다.
 * 데모: GitHub Pages(정적)에서는 data/<code>.json 스냅샷을 fetch 한다.
 *       실서비스에서는 이 fetch 대상을 FastAPI 엔드포인트로 바꾸면 된다.
 */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const won = n => (n == null ? "—" : Number(n).toLocaleString() + "원");
  const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const INDEX = "data/index.json";
  const base = () => window.HannunConfig.get();          // 배포 백엔드 주소(없으면 데모)
  const isLive = () => !!base();

  // 실시간 모드에서 보여줄 예시 종목(실제 상장 코드)
  const LIVE_EXAMPLES = [
    ["삼성전자", "005930"], ["SK하이닉스", "000660"], ["에코프로비엠", "247540"],
    ["NAVER", "035420"], ["카카오", "035720"], ["현대차", "005380"],
  ];

  function updateMode() {
    const badge = $("#mode");
    const banner = $("#banner");
    if (isLive()) {
      let host = base();
      try { host = new URL(base()).host; } catch (_) {}
      badge.textContent = "🟢 실시간 · " + host;
      badge.className = "mode-badge live";
      banner.innerHTML =
        `🟢 <b>실시간 모드</b> — 백엔드(${esc(host)})에서 KRX·DART 데이터를 받아 분석합니다. ` +
        `기준 시점은 장 마감/공시 기준입니다.`;
    } else {
      badge.textContent = "🧪 데모 모드";
      badge.className = "mode-badge demo";
      // 데모 배너는 index.html 기본 문구 유지
    }
  }

  function renderChips(list) {
    const chips = $("#chips");
    chips.innerHTML = "";
    list.forEach(([name, code]) => {
      const c = el("button", "chip", `${esc(name)} <span style="opacity:.6">${code}</span>`);
      c.onclick = () => { $("#q").value = code; analyze(code); };
      chips.appendChild(c);
    });
  }

  async function loadIndex() {
    updateMode();
    if (isLive()) {
      renderChips(LIVE_EXAMPLES);
      analyze(LIVE_EXAMPLES[0][1]);
      return;
    }
    try {
      const { stocks } = await (await fetch(INDEX)).json();
      renderChips(stocks.map(s => [s.name, s.code]));
      if (stocks[0]) analyze(stocks[0].code);
    } catch (e) {
      $("#result").innerHTML = `<div class="card loading">종목 목록을 불러오지 못했습니다.</div>`;
    }
  }

  async function analyze(codeOrName) {
    const q = (codeOrName || "").trim();
    if (!q) return;
    $("#result").innerHTML = `<div class="card loading">분석 데이터를 계산해 불러오는 중…</div>`;

    // ---- 실시간 모드: 배포 백엔드 호출 (종목명·코드 모두 지원) ----
    if (isLive()) {
      try {
        const res = await fetch(`${base()}/api/analyze?query=${encodeURIComponent(q)}`);
        if (!res.ok) {
          let msg = `요청 실패 (HTTP ${res.status})`;
          try { msg = (await res.json()).detail || msg; } catch (_) {}
          throw new Error(msg);
        }
        render(await res.json());
      } catch (e) {
        $("#result").innerHTML =
          `<div class="card loading">‘${esc(q)}’ 분석 실패<br>
           <span style="font-size:13px">${esc(e.message)}</span><br><br>
           백엔드 주소·상태를 확인하세요. (연결 해제하려면 <b>백엔드 연결</b> → 빈칸 저장)</div>`;
      }
      return;
    }

    // ---- 데모 모드: 정적 스냅샷 (종목명이면 index에서 매칭) ----
    let code = q;
    if (!/^\d{6}$/.test(q)) {
      try {
        const { stocks } = await (await fetch(INDEX)).json();
        const hit = stocks.find(s => s.name.includes(q) || q.includes(s.name));
        if (hit) code = hit.code;
      } catch (_) {}
    }
    try {
      const res = await fetch(`data/${code}.json`);
      if (!res.ok) throw new Error("not found");
      render(await res.json());
    } catch (e) {
      $("#result").innerHTML =
        `<div class="card loading">‘${esc(q)}’ 에 대한 데모 데이터가 없습니다.<br>
         아래 예시 종목을 눌러보거나, <b>백엔드 연결</b>로 실시간 모드를 켜세요.<br>
         <span style="font-size:13px">(데모는 샘플 3종만 제공)</span></div>`;
    }
  }

  function connectBackend() {
    const cur = base();
    const v = window.prompt(
      "배포한 백엔드 주소를 입력하세요 (예: https://hannun-stock-api.onrender.com)\n" +
      "비워두고 확인하면 데모 모드로 돌아갑니다.", cur || "");
    if (v === null) return;                 // 취소
    window.HannunConfig.set(v);
    loadIndex();
  }

  function badgeNode(b) {
    const n = el("div", "badge");
    const top = el("div", "top");
    top.appendChild(el("span", "key", esc(b.key)));
    if (b.raw) top.appendChild(el("span", "raw", `(${esc(b.raw)})`));
    if (b.confidence) top.appendChild(el("span", `cf cf-${b.confidence}`, `신뢰도 ${b.confidence}`));
    n.appendChild(top);
    if (b.counter_risk) n.appendChild(el("div", "risk", esc(b.counter_risk)));
    return n;
  }

  function axisCard(icon, title, badges, metricsHtml, score) {
    const c = el("div", "card");
    const head = el("div", "axis-head");
    head.appendChild(el("span", "ico", icon));
    head.appendChild(el("h3", null, title));
    if (score != null) {
      head.appendChild(el("span", "score", `${score}<span style="opacity:.5">/100</span>`));
    }
    c.appendChild(head);
    if (score != null) {
      const cls = score >= 70 ? "good" : score >= 45 ? "mid" : "bad";
      const bar = el("div", "bar");
      bar.appendChild(el("i", cls));
      bar.firstChild.style.width = score + "%";
      c.appendChild(bar);
    }
    (badges || []).forEach(b => c.appendChild(badgeNode(b)));
    if (metricsHtml) c.appendChild(el("div", "metrics", metricsHtml));
    return c;
  }

  function pct(x) { return x == null ? "—" : (x * 100).toFixed(1) + "%"; }

  function render(d) {
    window.__lastChart = d.chart; // 리사이즈 재드로우용
    const root = $("#result");
    root.innerHTML = "";
    const v = d.verdict, m = d.meta, ax = d.axes;

    // ---------- 종합 카드 ----------
    const vc = el("div", "card");
    const grid = el("div", `verdict ${v.signal}`);
    grid.appendChild(el("div", `light ${v.signal}`, v.signal_emoji));
    const info = el("div");
    info.appendChild(el("div", "sub",
      `${esc(m.name)} · ${esc(m.code)} · ${esc(m.market)} · ${esc(m.sector)} · 현재가 ${won(m.price)}`));
    info.appendChild(el("div", `headline sig-${v.signal}`, `${esc(v.signal_label)} · ${esc(v.combo)}`));
    info.appendChild(el("div", "oneliner", esc(v.one_liner)));
    const meta = el("div", "metaline");
    meta.appendChild(el("span", `pill risk-${v.risk_grade}`, `위험 등급: ${esc(v.risk_label)}`));
    meta.appendChild(el("span", "pill", `종합 신뢰도: ${esc(v.confidence)}`));
    info.appendChild(meta);
    grid.appendChild(info);
    vc.appendChild(grid);
    if (v.conflict && v.conflict.exists) {
      vc.appendChild(el("div", "conflict",
        `🔀 <b>차트와 펀더멘탈이 다르게 말하고 있어요.</b> ${esc(v.conflict.note)}`));
    }
    root.appendChild(vc);

    // ---------- 구간 카드 ----------
    const rc = el("div", "card");
    rc.appendChild(el("h2", null, "🎯 참고 구간 (확정 가격 아님)"));
    rc.appendChild(el("div", "sub", esc(d.ranges.basis)));
    const rg = el("div", "range-grid");
    const box = (cls, lbl, val) => {
      const b = el("div", `range-box ${cls}`);
      b.appendChild(el("div", "lbl", lbl));
      b.appendChild(el("div", "val", val));
      return b;
    };
    rg.appendChild(box("buy", "매수 관심 구간",
      `${Number(d.ranges.buy_zone[0]).toLocaleString()}~${Number(d.ranges.buy_zone[1]).toLocaleString()}`));
    rg.appendChild(box("stop", "손절 기준(참고)", Number(d.ranges.stop_loss).toLocaleString()));
    rg.appendChild(box("target", "목표 구간",
      `${Number(d.ranges.target_zone[0]).toLocaleString()}~${Number(d.ranges.target_zone[1]).toLocaleString()}`));
    rc.appendChild(rg);
    const inv = el("div", "invalid");
    inv.appendChild(el("div", "t", "🧭 판단을 바꿀 조건"));
    const ul = el("ul");
    d.ranges.invalidation.forEach(x => ul.appendChild(el("li", null, esc(x))));
    inv.appendChild(ul);
    rc.appendChild(inv);
    root.appendChild(rc);

    // ---------- 차트 카드 ----------
    const cc = el("div", "card");
    cc.appendChild(el("h2", null, "📈 차트 흐름"));
    cc.appendChild(el("div", "sub", "최근 90거래일 · 캔들 + 이동평균(5·20·60·120일)"));
    const cw = el("div", "chart-wrap");
    const cv = el("canvas"); cv.id = "chart";
    cw.appendChild(cv);
    cc.appendChild(cw);
    const lg = el("div", "legend");
    [["5", "5일"], ["20", "20일"], ["60", "60일"], ["120", "120일"]].forEach(([k, t]) => {
      const s = el("span");
      const i = el("i"); i.style.background = window.StockChart.MA_COLORS[k];
      s.appendChild(i); s.appendChild(document.createTextNode(t));
      lg.appendChild(s);
    });
    cc.appendChild(lg);
    root.appendChild(cc);
    requestAnimationFrame(() => window.StockChart.draw(cv, d.chart));

    // ---------- 4축 카드 ----------
    const axesWrap = el("div", "axes");
    const t = ax.technical.metrics;
    axesWrap.appendChild(axisCard("📊", "축1 · 차트 흐름 (기술적)", ax.technical.badges,
      `RSI <code>${t.rsi14}</code> · MACD <code>${t.macd.macd}</code>/<code>${t.macd.signal}</code>
       · 거래량 <code>${t.vol_ratio}배</code> · 20일 변동성σ <code>${t.sigma.toFixed(3)}</code>
       · 지지 <code>${won(t.support)}</code> · 저항 <code>${won(t.resistance)}</code>`));

    const f = ax.flow.metrics;
    axesWrap.appendChild(axisCard("🤝", "축2 · 수급 (누가 사나)", ax.flow.badges,
      `외국인 5일 <code>${f.foreign_5d.toLocaleString()}</code> · 20일 <code>${f.foreign_20d.toLocaleString()}</code>
       · 기관 5일 <code>${f.inst_5d.toLocaleString()}</code> · 20일 <code>${f.inst_20d.toLocaleString()}</code> (주)`));

    const g = ax.growth.metrics;
    axesWrap.appendChild(axisCard("🌱", "축3-A · 성장성", ax.growth.badges,
      `매출 3년CAGR <code>${pct(g.rev_cagr_3y)}</code> · 영업이익 YoY <code>${pct(g.op_growth_yoy)}</code>
       · EPS YoY <code>${pct(g.eps_growth_yoy)}</code> · PEG <code>${g.peg == null ? "적용불가" : g.peg}</code>`,
      ax.growth.score));

    const st = ax.stability.metrics;
    axesWrap.appendChild(axisCard("🛡️", "축3-B · 안정성", ax.stability.badges,
      `부채비율 <code>${pct(st.debt_ratio)}</code> · 유동비율 <code>${pct(st.current_ratio)}</code>
       · 이자보상배율 <code>${st.interest_coverage}배</code> · FCF <code>${st.fcf_positive ? "+" : "−"}</code>
       · 영업현금/순이익 <code>${st.ocf_vs_ni}</code> · 관리종목 <code>${st.watch_issue ? "해당" : "아님"}</code>`,
      ax.stability.score));

    const val = ax.valuation.metrics;
    const trap = val.value_trap && val.value_trap.suspected
      ? `<div class="risk" style="margin-top:8px">${esc(val.value_trap.reason)}</div>` : "";
    const valCard = axisCard("💰", "축4 · 가격 매력도 (3축 교차검증)", ax.valuation.badges,
      `PER <code>${val.per == null ? "적자·N/A" : val.per}</code> · PBR <code>${val.pbr}</code>
       · PEG <code>${val.peg == null ? "적용불가" : val.peg}</code>
       · 업종 PER 백분위 <code>${val.sector_per_pct}%</code> · 역사적 PER 위치 <code>${val.hist_per_pct}%</code>
       <br><span style="opacity:.7">평가방식: ${esc(val.method)}</span>`);
    if (trap) valCard.insertAdjacentHTML("beforeend", trap);
    axesWrap.appendChild(valCard);
    root.appendChild(axesWrap);

    // ---------- 하단: 출처 · 기준시점 · 면책 ----------
    const ft = el("div", "footer");
    ft.appendChild(el("div", "disc", "⚠ " + esc(d.disclaimer)));
    const src = el("div", "src");
    src.appendChild(el("span", null, `데이터 출처: ${m.sources.map(esc).join(" · ")}`));
    src.appendChild(el("span", null, `기준 시점(장 마감): ${esc(m.as_of)}`));
    src.appendChild(el("span", null, `분석 생성: ${esc(m.generated_at)}`));
    src.appendChild(el("span", null, m.is_sample ? "※ 데모 · 합성 샘플 데이터" : "실데이터"));
    ft.appendChild(src);
    root.appendChild(ft);

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ---------- 이벤트 ----------
  window.addEventListener("DOMContentLoaded", () => {
    $("#go").onclick = () => analyze($("#q").value);
    $("#conn").onclick = connectBackend;
    $("#q").addEventListener("keydown", e => { if (e.key === "Enter") analyze($("#q").value); });
    window.addEventListener("resize", () => {
      const cv = $("#chart");
      if (cv && window.__lastChart) window.StockChart.draw(cv, window.__lastChart);
    });
    loadIndex();
  });
})();
