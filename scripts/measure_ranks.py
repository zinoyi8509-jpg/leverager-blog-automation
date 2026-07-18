#!/usr/bin/env python3
"""매일용 측정 스크립트 — 어제 서브 키워드만 측정 (약 10~30개).
전체 측정은 weekly_reports.py 에서 매주 월요일 수행.
"""
import os, sys, json, datetime, time
from pathlib import Path
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history.json"

CLIENTS = {
    "chanwoo0919", "cowper7710", "cdo27953", "kbtax0503",
    "sh33391", "shingonggandesign02", "cdo2795", "cdo27952",
    "cdo27951", "leverager_solution", "kkomkkomcleaning",
}
TIS = {"masil0919", "cdo2795", "leverager-solution"}
OUR_IDS = CLIENTS | TIS


def extract_ranks(page):
    return page.evaluate("""
    () => {
      const links = Array.from(document.querySelectorAll('a'));
      const postLinks = links
        .filter(a => /blog\\.naver\\.com\\/[a-zA-Z0-9_]+\\/\\d+/.test(a.href) ||
                     /\\.tistory\\.com\\/\\d+/.test(a.href))
        .map(a => ({href: a.href.split('?')[0], text: (a.textContent || '').trim().slice(0, 100)}));
      const seen = new Set();
      const cards = postLinks.filter(l => {
        if (seen.has(l.href)) return false;
        seen.add(l.href); return true;
      });
      return cards.slice(0, 30).map((l, i) => {
        const m = l.href.match(/blog\\.naver\\.com\\/([a-zA-Z0-9_]+)\\/(\\d+)/) ||
                  l.href.match(/([a-zA-Z0-9_]+)\\.tistory\\.com\\/(\\d+)/);
        return {rank: i+1, id: m ? m[1] : null, text: l.text, href: l.href};
      });
    }
    """)


def search(page, kw):
    url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&sm=tab_jum&query={quote_plus(kw)}"
    page.goto(url, wait_until="networkidle", timeout=20000)
    time.sleep(1.2)
    cards = extract_ranks(page)
    ours = [c for c in cards if c["id"] in OUR_IDS]
    if not ours:
        time.sleep(1.0)
        page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(2.0)
        cards = extract_ranks(page)
        ours = [c for c in cards if c["id"] in OUR_IDS]
    by_id = {}
    for c in ours:
        by_id.setdefault(c["id"], []).append(c)
    return by_id


def main():
    h = json.load(open(HIST, encoding="utf-8"))
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    today = datetime.date.today().isoformat()

    # 어제 발행 서브 키워드 수집
    jobs = {}
    for bid, b in (h.get("blogs") or {}).items():
        if bid.startswith("_"): continue
        sub = b.get("keywords", {}).get("sub") or {}
        for ym, node in sub.items():
            by_date = (node or {}).get("by_date") or {}
            if yesterday in by_date:
                for kw in by_date[yesterday]:
                    jobs.setdefault(bid, []).append(kw)

    if not jobs:
        print(f"📭 어제({yesterday}) 발행 서브 키워드 없음 — 스킵")
        return

    total = sum(len(v) for v in jobs.values())
    print(f"📡 측정: {total}개 키워드 · {len(jobs)}개 회사 · 어제={yesterday}")

    bucket = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        i = 0
        for bid, kws in jobs.items():
            for kw in kws:
                i += 1
                try:
                    by_id = search(page, kw)
                    cards = by_id.get(bid, [])
                    if cards:
                        ranks = sorted(c["rank"] for c in cards)
                        item = {"kw": kw, "rank": ranks[0]}
                        if len(ranks) > 1:
                            item["extra_ranks"] = ranks[1:]
                        item["title"] = cards[0]["text"][:60]
                    else:
                        item = {"kw": kw, "rank": None, "note": "권외"}
                    bucket.setdefault(bid, []).append(item)
                    print(f"  [{i}/{total}] {bid}: {kw} → {item.get('rank') or '권외'}")
                except Exception as ex:
                    print(f"  [{i}/{total}] {bid}: {kw} ⚠ {ex}")
                    bucket.setdefault(bid, []).append({"kw": kw, "rank": None, "note": str(ex)[:80]})
        browser.close()

    for bid, items in bucket.items():
        kr = h["blogs"][bid].setdefault("keyword_rank", {})
        rec = kr.get(today) or {"source": "playwright_실측", "items": []}
        by_kw = {it["kw"]: it for it in rec.get("items", [])}
        for it in items:
            by_kw[it["kw"]] = it
        rec["items"] = list(by_kw.values())
        rec["source"] = "playwright_실측"
        rec["daily_partial"] = True
        kr[today] = rec

    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ 매일 측정 완료 (today={today})")
    for bid, items in bucket.items():
        p1 = sum(1 for it in items if it.get("rank") and it["rank"] <= 10)
        print(f"  {bid}: {len(items)}개 / 1페이지 {p1}")


if __name__ == "__main__":
    main()
