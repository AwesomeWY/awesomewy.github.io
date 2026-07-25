/*
 * chart.js — 캔들 + 이동평균선(5/20/60/120) 렌더러 (Canvas, 의존성 없음)
 * 원칙: 이 파일은 '그리기'만 한다. 이동평균 등 수치는 백엔드(Python)가 계산해
 *       chart.ma 로 내려준 값을 그대로 사용한다. JS는 지표를 재계산하지 않는다.
 */
(function () {
  const MA_COLORS = { "5": "#8a8f9c", "20": "#2f6df6", "60": "#c98a06", "120": "#8b5cf6" };

  function draw(canvas, chart) {
    const ohlcv = chart.ohlcv;
    const ma = chart.ma;
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 900;
    const cssH = canvas.clientHeight || 320;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const padL = 8, padR = 56, padT = 12, padB = 22;
    const view = ohlcv.slice(-90); // 최근 90봉만 표시
    const offset = ohlcv.length - view.length;
    const highs = view.map(r => r.h), lows = view.map(r => r.l);
    let hi = Math.max(...highs), lo = Math.min(...lows);
    const pad = (hi - lo) * 0.08; hi += pad; lo -= pad;

    const plotW = cssW - padL - padR, plotH = cssH - padT - padB;
    const x = i => padL + (plotW * (i + 0.5)) / view.length;
    const y = p => padT + plotH * (1 - (p - lo) / (hi - lo));
    const bw = Math.max(1.2, (plotW / view.length) * 0.62);

    const css = getComputedStyle(document.documentElement);
    const line = css.getPropertyValue("--line").trim() || "#e6e9f0";
    const muted = css.getPropertyValue("--muted").trim() || "#667085";
    const up = "#e15241", down = "#2f6df6"; // 한국 관행: 상승=빨강, 하락=파랑

    // 가로 그리드 + 가격 눈금
    ctx.font = "11px ui-monospace, monospace";
    ctx.textBaseline = "middle";
    ctx.strokeStyle = line; ctx.fillStyle = muted; ctx.lineWidth = 1;
    for (let g = 0; g <= 4; g++) {
      const p = lo + ((hi - lo) * g) / 4;
      const yy = y(p);
      ctx.globalAlpha = 0.5;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(cssW - padR, yy); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillText(Math.round(p).toLocaleString(), cssW - padR + 6, yy);
    }

    // 캔들
    for (let i = 0; i < view.length; i++) {
      const r = view[i], cx = x(i);
      const color = r.c >= r.o ? up : down;
      ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(cx, y(r.h)); ctx.lineTo(cx, y(r.l)); ctx.stroke();
      const yo = y(r.o), yc = y(r.c);
      const top = Math.min(yo, yc), h = Math.max(1, Math.abs(yc - yo));
      ctx.fillRect(cx - bw / 2, top, bw, h);
    }

    // 이동평균선
    Object.keys(MA_COLORS).forEach(w => {
      const series = ma[w]; if (!series) return;
      ctx.strokeStyle = MA_COLORS[w]; ctx.lineWidth = 1.4; ctx.beginPath();
      let started = false;
      for (let i = 0; i < view.length; i++) {
        const v = series[offset + i];
        if (v == null) continue;
        const px = x(i), py = y(v);
        if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
      }
      ctx.stroke();
    });
  }

  window.StockChart = { draw, MA_COLORS };
})();
