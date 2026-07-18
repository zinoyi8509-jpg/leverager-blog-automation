#!/usr/bin/env python3
"""
윤팀장 내부 운영 보고서 (블로그별 모니터링).
- 메인 키워드(영구) + 서브 키워드(월별) 1~10위 측정 결과
- 4가지 지표 일별: 조회수·순방문자·체류시간·검색유입
- 운영 액션 가이드 자동 추출

사용: python3 dashboards/scripts/internal_report.py [회사ID] [측정일자]
  예) internal_report.py cowper 2026-06-22

산출: dashboards/reports/internal/{회사}_윤팀장_운영보고서_{날짜}.pdf
"""
import sys, os, json, html, datetime
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HIST = os.path.join(ROOT, "data", "history.json")
ODIR = os.path.join(ROOT, "reports", "internal")
import shutil as _shutil
CHROME = (_shutil.which("google-chrome") or _shutil.which("chromium")
          or _shutil.which("chromium-browser")
          or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
e = lambda s: html.escape(str(s), quote=True)

CLIENTS = {
    "cowper": ("cowper7710", "카우퍼"),
    "masil":  ("chanwoo0919", "마실"),
    "mecca":  ("cdo27953", "메카"),
    "dawon":  ("kbtax0503", "다원세무회계"),
    "seohwi": ("sh33391", "서휘건설"),
    "shingonggan": ("shingonggandesign02", "신공간디자인"),
    "gunterior": ("cdo2795", "건테리어"),
    "gunteriors": ("cdo27952", "건테리어스"),
    "gunterior_house": ("cdo27951", "건테리어주택"),
    "leso": ("leverager_solution", "레솔"),
    "kkomkkom": ("kkomkkomcleaning", "꼼꼼종합클린"),
}

def fmt_dur(secs):
    if not secs: return "-"
    m, s = divmod(int(secs), 60)
    if m == 0: return f"{s}s"
    return f"{m}m {s}s"

def rank_chip(rank, extra=None, with_action=True):
    """순위 칩. with_action=True면 '재발행 필요' 액션 라벨 추가 (메인 전용)."""
    if rank is None:
        if with_action:
            return f'<span class="chip-none">순위 없음</span> <span class="no-show">재발행 필요</span>'
        return f'<span class="chip-none">순위 없음</span>'
    extra_str = f' <em>+{len(extra)}건</em>' if extra else ''
    if rank == 1: cls = "rk-1"
    elif rank == 2: cls = "rk-2"
    elif rank == 3: cls = "rk-3"
    elif rank <= 5: cls = "rk-mid"
    elif 6 <= rank <= 9:
        # 6~9위는 1페이지 끝자락 — 메인 키워드에만 '재발행 필요' 라벨
        chip = f'<span class="chip rk-weak"><b>{rank}위</b>{extra_str}</span>'
        if with_action:
            return f'{chip} <span class="no-show">재발행 필요</span>'
        return chip
    else:
        cls = "rk-low"
    return f'<span class="chip {cls}"><b>{rank}위</b>{extra_str}</span>'


def build(client_id, today=None):
    nv, name = CLIENTS[client_id]
    today = today or datetime.date.today().isoformat()
    h = json.load(open(HIST, encoding="utf-8"))
    blog = h["blogs"][nv]
    main_kws = blog.get("keywords", {}).get("main", [])
    cur_month = today[:7]  # 2026-06
    sub_node = blog.get("keywords", {}).get("sub", {}).get(cur_month, {})
    sub_kws = sub_node.get("unique_keywords", [])
    sub_by_date = sub_node.get("by_date", {})

    # 최신 measurement
    kr = blog.get("keyword_rank", {})
    latest = sorted([d for d in kr if (kr[d] or {}).get("source") == "playwright_실측"], reverse=True)
    rank_data = kr[latest[0]] if latest else {"items": []}
    rank_date = latest[0] if latest else "(미측정)"
    items = {it["kw"]: it for it in rank_data.get("items", [])}

    daily = blog.get("daily", {})
    month_days = sorted([d for d in daily if d.startswith(cur_month)])

    sw = blog.get("search_weekly", {})
    latest_sw = sorted(sw.keys(), reverse=True)
    sw_data = sw[latest_sw[0]] if latest_sw else None
    sw_period = latest_sw[0] if latest_sw else None

    S = []
    S.append(f'<div class="wrap">')
    # 커버
    S.append(f'<div class="cover">'
             f'<div class="brand">윤팀장 운영 점검 보고서</div>'
             f'<div class="ttl">{e(name)} ({nv})</div>'
             f'<div class="meta">측정일자 {e(rank_date)} · 보고서 작성 {today}</div></div>')

    # KPI
    main_in = sum(1 for kw in main_kws if items.get(kw, {}).get("rank"))
    main_avg = round(sum(items[kw]["rank"] for kw in main_kws if items.get(kw, {}).get("rank"))/main_in, 2) if main_in else None
    sub_in = sum(1 for kw in sub_kws if items.get(kw, {}).get("rank"))
    multi_total = sum(len(items[kw].get("extra_ranks", [])) for kw in main_kws + sub_kws if items.get(kw, {}).get("rank"))

    S.append('<div class="kpi">')
    S.append(f'<div class="k"><div class="l">메인 키워드 1페이지</div><div class="v">{main_in}<small>/{len(main_kws)}</small></div></div>')
    if main_avg: S.append(f'<div class="k"><div class="l">메인 평균 순위</div><div class="v">{main_avg}<small>위</small></div></div>')
    S.append(f'<div class="k"><div class="l">서브 키워드 1페이지</div><div class="v">{sub_in}<small>/{len(sub_kws)}</small></div></div>')
    S.append(f'<div class="k"><div class="l">다중 노출 추가 글</div><div class="v">+{multi_total}<small>건</small></div></div>')
    S.append('</div>')

    # 메인 키워드 — CSS multi-column 자연 흐름 (페이지 넘어가도 좌→우 순서 유지)
    rows = ''
    for i, kw in enumerate(main_kws, 1):
        it = items.get(kw, {})
        rows += (f'<div class="mk-row"><span class="mk-no">{i}.</span> '
                 f'<span class="mk-kw">{e(kw)}</span> '
                 f'<span class="mk-rk">{rank_chip(it.get("rank"), it.get("extra_ranks"))}</span></div>')
    S.append(f'<div class="sec"><h2>🎯 메인 키워드 — ({len(main_kws)}개)</h2>'
             f'<div class="main-flow">{rows}</div></div>')

    # 서브 키워드 표 — 발행일순(날짜 컬럼 추가)
    if sub_kws:
        # by_date에서 (날짜, 키워드) 페어 생성 — 발행 순서 그대로
        date_kw_pairs = []
        seen_kw = set()
        for d in sorted(sub_by_date):
            for kw in sub_by_date[d]:
                if kw in seen_kw or kw not in sub_kws:  # 중복·메인키워드 제외
                    continue
                seen_kw.add(kw)
                date_kw_pairs.append((d, kw))
        S.append(f'<div class="sec"><h2>🔁 서브 키워드 — {cur_month[5:7]}월 발행 글 타겟 ({len(date_kw_pairs)}개, 발행일순, 다음달 1일 초기화)</h2>'
                 '<table class="kw-tbl"><thead>'
                 '<tr><th class="r">No.</th><th class="nowrap">발행일</th><th>키워드</th><th>순위</th><th>제목</th></tr></thead><tbody>')
        for i, (d, kw) in enumerate(date_kw_pairs, 1):
            it = items.get(kw, {})
            rank = it.get("rank")
            extra = it.get("extra_ranks")
            title = it.get("title", "") if rank else ""
            day_str = f"{int(d[5:7])}/{int(d[8:10])}"
            S.append(f'<tr><td class="r">{i}</td><td class="nowrap"><b>{day_str}</b></td>'
                     f'<td><b>{e(kw)}</b></td>'
                     f'<td>{rank_chip(rank, extra, with_action=False)}</td><td class="muted">{e(title[:40])}</td></tr>')
        S.append('</tbody></table></div>')

    # 📅 이번 달 발행 키워드 순위 (사용자 지시 2026-07-13: 1~5위만 표시·6위 이하는 '노출없음')
    if sub_by_date:
        month_dates = sorted([d for d in sub_by_date if d.startswith(cur_month)])
        if month_dates:
            total_pub_kws = sum(len(sub_by_date[d]) for d in month_dates)
            S.append(f'<div class="sec"><h2>📅 {cur_month[5:7]}월 발행 키워드 · 순위 (날짜별 {total_pub_kws}개, 6위 이하는 노출없음)</h2>'
                     '<div class="pub-list">')
            for d in month_dates:
                day_str = f"{int(d[5:7])}/{int(d[8:10]):02d}"
                S.append(f'<div class="pub-day"><div class="pd-date">📌 {day_str}</div><ul class="pd-kws">')
                for kw in sub_by_date[d]:
                    it = items.get(kw, {})
                    rank = it.get("rank")
                    if rank and rank <= 5:
                        cls = "rk-1" if rank == 1 else "rk-2" if rank == 2 else "rk-3" if rank == 3 else "rk-mid"
                        disp = f'<span class="chip {cls}"><b>{rank}위</b></span>'
                    else:
                        disp = '<span class="chip-none">노출없음</span>'
                    S.append(f'<li><span class="pd-kw">{e(kw)}</span> {disp}</li>')
                S.append('</ul></div>')
            S.append('</div></div>')

    # AI브리핑 인용수 — 헤더만 (수기 입력 영역)
    S.append('<div class="sec"><h2>🔁 AI브리핑 인용수 — </h2></div>')

    # 4가지 지표 일별 표
    if month_days:
        has_est = any(daily[d].get('views_source') == '그래프 추정' for d in month_days)
        est_note = ' <span class="est-note">* 조회수는 일간현황 그래프 추정 (★ 표시 = 일별 표 확정값)</span>' if has_est else ''
        S.append(f'<div class="sec"><h2>📊 {cur_month[5:7]}월 일별 지표 ({len(month_days)}일){est_note}</h2>'
                 '<table class="day-tbl"><thead><tr>'
                 '<th>날짜</th><th class="r">조회수</th><th class="r">순방문</th><th class="r">체류시간</th>'
                 '</tr></thead><tbody>')
        for d in month_days:
            v = daily[d]
            views = v.get("views")
            views_str = '-'
            if views is not None:
                if v.get('views_source') == '그래프 추정':
                    views_str = f'<span class="muted">~{views}</span>'
                else:
                    views_str = f'<b>{views} ★</b>'
            vis = v.get("visitors", "-")
            dur = fmt_dur(v.get("avg_duration_sec"))
            S.append(f'<tr><td><b>{d[5:]}</b></td><td class="r">{views_str}</td>'
                     f'<td class="r">{vis}</td><td class="r">{dur}</td></tr>')
        # 요약 행
        v_cnt = sum(1 for d in month_days if daily[d].get("views"))
        avg_views = round(sum(daily[d].get("views",0) for d in month_days if daily[d].get("views"))/v_cnt, 1) if v_cnt else "-"
        avg_vis = round(sum(daily[d].get("visitors",0) for d in month_days if daily[d].get("visitors"))/sum(1 for d in month_days if daily[d].get("visitors")), 1)
        avg_dur = sum(daily[d].get("avg_duration_sec",0) for d in month_days if daily[d].get("avg_duration_sec"))//sum(1 for d in month_days if daily[d].get("avg_duration_sec"))
        S.append(f'<tr class="sum"><td><b>평균</b></td>'
                 f'<td class="r"><b>{avg_views}</b></td>'
                 f'<td class="r"><b>{avg_vis}명</b></td>'
                 f'<td class="r"><b>{fmt_dur(avg_dur)}</b></td></tr>')
        S.append('</tbody></table></div>')

    # 검색 유입 키워드
    if sw_data:
        S.append(f'<div class="sec"><h2>🔎 주간 검색 유입 ({sw_period}) — 검색 비중 {sw_data["search_share"]}%</h2>'
                 '<table class="day-tbl"><thead><tr><th>검색어</th><th class="r">비중</th></tr></thead><tbody>')
        for kw in sw_data.get("keywords", [])[:15]:
            S.append(f'<tr><td>{e(kw["k"])}</td><td class="r">{kw["p"]}%</td></tr>')
        S.append('</tbody></table></div>')

    # 운영 액션 가이드 (자동 추출)
    actions = []
    # 하락 위험: 메인 중 5위 이하 + 다중 노출 없음
    risky = [kw for kw in main_kws if items.get(kw, {}).get("rank") and items[kw]["rank"] >= 5 and not items[kw].get("extra_ranks")]
    if risky:
        actions.append(("🚨 보강 필요 (5위 이하·단일 노출)", risky))
    # 순위 없음 키워드
    missing = [kw for kw in main_kws + sub_kws if not items.get(kw, {}).get("rank")]
    if missing:
        actions.append(("❌ 순위 없음 (콘텐츠 신규 필요)", missing))
    # 다중 노출 강세 (3건+)
    strong = sorted(
        [(kw, items[kw]["rank"], len(items[kw].get("extra_ranks", []))) for kw in main_kws + sub_kws
         if items.get(kw, {}).get("rank") and len(items[kw].get("extra_ranks", [])) >= 3],
        key=lambda x: -x[2]
    )
    if strong:
        actions.append(("💪 다중 노출 강세 (3건+ 동시 노출)",
                        [f"{kw} ({rank}위 + {n}건)" for kw, rank, n in strong[:10]]))

    if actions:
        S.append('<div class="sec"><h2>📌 운영 액션 가이드</h2>')
        for title, items_list in actions:
            S.append(f'<div class="action-box"><div class="action-ttl">{title}</div><ul>')
            for kw in items_list:
                S.append(f'<li>{e(kw)}</li>')
            S.append('</ul></div>')
        S.append('</div>')

    S.append('</div>')

    CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:#1c2127;background:#fff;line-height:1.5}
.wrap{max-width:800px;margin:0 auto;padding:0 28px 32px}
.cover{background:linear-gradient(135deg,#0f172a,#334155);color:#fff;margin:0 -28px 18px;padding:26px 28px}
.cover .brand{font-size:12px;opacity:.75;letter-spacing:1px;font-weight:700}
.cover .ttl{font-size:24px;font-weight:800;margin-top:6px}
.cover .meta{font-size:12.5px;opacity:.85;margin-top:8px}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:18px}
.k{background:#f8fafc;border:1px solid #e2e8f0;border-radius:9px;padding:11px 13px}
.k .l{font-size:11px;color:#64748b;font-weight:600}
.k .v{font-size:21px;font-weight:800;color:#0f172a;margin-top:3px}
.k .v small{font-size:11px;font-weight:600;color:#94a3b8}
.sec{margin-top:22px}
h2{font-size:15px;color:#0f172a;margin-bottom:10px;font-weight:800;break-after:avoid;page-break-after:avoid}
.est-note{font-size:10px;color:#94a3b8;font-weight:500}
.cat-tag{display:inline-block;font-size:10px;padding:1px 7px;border-radius:4px;font-weight:700}
.tag-main{background:#dbeafe;color:#1e40af}
.tag-sub{background:#dcfce7;color:#166534}
table{width:100%;border-collapse:collapse;font-size:12.5px}
.kw-tbl th,.kw-tbl td,.day-tbl th,.day-tbl td{border-bottom:1px solid #e5e7eb;padding:6px 8px;text-align:left}
.kw-tbl th,.day-tbl th{background:#f1f5f9;color:#475569;font-size:11px;font-weight:700;border-bottom:2px solid #cbd5e1}
/* 메인 키워드 자연 흐름 2단 — 페이지 넘어가도 좌→우 순서 유지 */
.main-flow{columns:2;column-gap:18px;column-fill:auto}
.mk-row{display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px dotted #e5e7eb;font-size:11px;break-inside:avoid;page-break-inside:avoid}
.mk-no{color:#94a3b8;font-size:10px;min-width:26px;text-align:right;flex-shrink:0}
.mk-kw{font-weight:700;color:#0f172a;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mk-rk{flex-shrink:0}
.main-flow .chip{font-size:9.5px;padding:1px 5px}
.main-flow .chip b{font-size:9.5px}
.main-flow .no-show{font-size:9px;padding:1px 4px}
.main-flow .chip-none{font-size:9.5px;padding:1px 5px}
.r{text-align:right}
.nowrap{white-space:nowrap}
.muted{color:#94a3b8;font-size:11px}
.sum{background:#f8fafc;font-weight:700}
.chip{display:inline-block;font-size:11px;padding:2px 8px;border-radius:6px;border:1px solid;white-space:nowrap}
.chip b{font-weight:800}
.chip em{font-size:10px;font-style:normal;color:#64748b;margin-left:3px}
.chip.rk-1{background:#fee2e2;color:#7f1d1d;border-color:#ef4444}.chip.rk-1 b{color:#dc2626}
.chip.rk-2{background:#dbeafe;color:#1e3a8a;border-color:#3b82f6}.chip.rk-2 b{color:#2563eb}
.chip.rk-3{background:#e5e7eb;color:#1f2937;border-color:#4b5563}.chip.rk-3 b{color:#374151}
.chip.rk-mid{background:#f3f4f6;color:#475569;border-color:#cbd5e1}
.chip.rk-weak{background:#f9fafb;color:#9ca3af;border-color:#e5e7eb}.chip.rk-weak b{color:#6b7280}
.no-show{display:inline-block;font-size:10.5px;padding:1px 7px;background:#fef2f2;color:#991b1b;border:1px solid #fca5a5;border-radius:5px;font-weight:700;margin-left:4px;vertical-align:middle}
.chip-none{display:inline-block;font-size:11px;padding:2px 8px;background:#fef2f2;color:#991b1b;border:1px solid #fca5a5;border-radius:6px}
/* 이번 달 발행 키워드 순위 섹션 (2026-07-13 신규) */
.pub-list{margin-top:6px}
.pub-day{margin-bottom:12px;break-inside:avoid;page-break-inside:avoid;background:#f9fafb;border-left:3px solid #6366f1;border-radius:6px;padding:8px 12px}
.pd-date{font-weight:700;color:#4338ca;font-size:12.5px;margin-bottom:5px}
.pd-kws{list-style:none;margin:0;padding:0;font-size:12px;line-height:1.9}
.pd-kws li{padding:2px 0;display:flex;justify-content:space-between;align-items:center;border-bottom:1px dashed #e5e7eb}
.pd-kws li:last-child{border-bottom:none}
.pd-kw{color:#111;flex:1}
.action-box{background:#fffbeb;border:1px solid #fde68a;border-left:3px solid #f59e0b;border-radius:8px;padding:11px 14px;margin-bottom:10px;break-inside:avoid}
.action-ttl{font-weight:800;color:#92400e;font-size:13px;margin-bottom:5px}
.action-box ul{padding-left:20px;font-size:12px;color:#451a03;line-height:1.7}
"""
    page = f'<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>{CSS}</style></head><body>{"".join(S)}</body></html>'

    os.makedirs(ODIR, exist_ok=True)
    base = os.path.join(ODIR, f"{name}_윤팀장_운영보고서_{today}")
    open(base + ".html", "w", encoding="utf-8").write(page)
    if os.path.exists(CHROME):
        os.system(f'"{CHROME}" --headless --disable-gpu --no-pdf-header-footer '
                  f'--print-to-pdf="{base}.pdf" "file://{base}.html" >/dev/null 2>&1')
    ok = os.path.exists(base + ".pdf") and os.path.getsize(base + ".pdf") > 1000
    if ok:
        try: os.remove(base + ".html")
        except OSError: pass
    print(f"✅ 윤팀장 운영 보고서 — {name}")
    print(f"   {base}.pdf {'✓' if ok else '실패'}")
    print(f"   메인 1페이지 {main_in}/{len(main_kws)} · 서브 1페이지 {sub_in}/{len(sub_kws)} · 다중노출 +{multi_total}건")


def main():
    args = sys.argv[1:]
    client = args[0] if args and args[0] in CLIENTS else "cowper"
    today = args[1] if len(args) > 1 else None
    build(client, today)


if __name__ == "__main__":
    main()
