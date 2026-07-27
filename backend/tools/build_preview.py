"""자체 완결형(single-file) 미리보기 빌더.

index.html/assets/data 를 하나의 HTML로 합쳐, 서버·GitHub Pages 없이도 열리는
미리보기를 만든다. 상대경로 data/*.json fetch 는 임베드된 데이터로 가로챈다.
출력: 인자로 받은 경로(기본 scratchpad/preview.html)
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def main(out_path):
    css = read("assets/styles.css")
    config_js = read("assets/config.js")
    chart_js = read("assets/chart.js")
    app_js = read("assets/app.js")

    codes = ["index", "005930", "247540", "000000"]
    embedded = {f"data/{c}.json": json.loads(read(f"data/{c}.json")) for c in codes}

    # index.html 의 <div class="wrap">...</div> 본문만 추출
    html = read("index.html")
    body = re.search(r'<div class="wrap">.*?</div>\s*(?=<script)', html, re.S)
    wrap = body.group(0) if body else html

    # 상대 fetch 를 임베드 데이터로 가로채는 shim (config.js 보다 먼저 로드)
    shim = (
        "window.__EMBEDDED__ = " + json.dumps(embedded, ensure_ascii=False) + ";\n"
        "(function(){\n"
        "  var _f = window.fetch ? window.fetch.bind(window) : null;\n"
        "  window.fetch = function(url, opts){\n"
        "    var key = String(url);\n"
        "    for (var k in window.__EMBEDDED__){\n"
        "      if (key.indexOf(k) !== -1) return Promise.resolve({ok:true, status:200,\n"
        "        json: function(){ return Promise.resolve(window.__EMBEDDED__[k]); }});\n"
        "    }\n"
        "    return _f ? _f(url, opts) : Promise.reject(new Error('offline preview'));\n"
        "  };\n"
        "})();\n"
    )

    out = (
        '<title>한눈·주식 — 미리보기</title>\n'
        f"<style>\n{css}\n</style>\n"
        f"{wrap}\n"
        f"<script>\n{shim}</script>\n"
        f"<script>\n{config_js}\n</script>\n"
        f"<script>\n{chart_js}\n</script>\n"
        f"<script>\n{app_js}\n</script>\n"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", out_path, f"({len(out):,} bytes)")


if __name__ == "__main__":
    default = os.path.join(
        "/tmp/claude-0/-home-user-awesomewy-github-io/"
        "80a6733d-90c2-53c2-99a4-20646f210e82/scratchpad", "preview.html")
    main(sys.argv[1] if len(sys.argv) > 1 else default)
