#!/usr/bin/env python3
"""네이버 블로그탭 실측 (Playwright 헤드리스) — 새 구조 지원 + 안전장치.

새 구조: blogs.{id}.keywords.main.categories[].groups[][]
안전장치: User-Agent 다양화, Retry(최대 3회), 티스토리 필터

사용:
  python3 scripts/measure_playwright.py <blog_id> [<blog_id> ...]
  python3 scripts/measure_playwright.py chanwoo0919 kbtax0503
"""
import sys, os, json, time, random
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data", "history.json")
TOP_N = 30
MAX_RETRY = 3

UA_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
]


def flatten_main(main_data):
    """categories 구조에서 모든 키워드 flat list로."""
    if isinstance(main_data, dict) and "categories" in main_data:
        return [kw for cat in main_data["categories"] for grp in cat.get("groups", []) for kw in grp]
    return list(main_data or [])


def collect_keywords(h, blog_id):
    """대상 블로그의 메인 + 서브 키워드 전체."""
    b = h["blogs"].get(blog_id)
    if not b: return []
    main = flatten_main(b.get("keywords", {}).get("main"))
    # 서브 (현재 월 unique_keywords)
    subs = []
    for month, node in (b.get("keywords", {}).get("sub") or {}).items():
        for kw in (node or {}).get("unique_keywords") or []:
            if kw not in subs: subs.append(kw)
    # 중복 제거
    all_kws = []
    seen = set()
    for kw in main + subs:
        if kw and kw not in seen:
            all_kws.append(kw)
            seen.add(kw)
    return all_kws


def parse_cards(page, blog_id):
    """네이버 검색결과에서 우리 블로그 순위 추출 (블로그+티스토리)."""
    return page.evaluate(f"""
    () => {{
      const links = Array.from(document.querySelectorAll('a'));
      const p = links
        .filter(a => /blog\\.naver\\.com\\/[a-zA-Z0-9_-]+\\/\\d+/.test(a.href) ||
                     /\\.tistory\\.com\\/\\d+/.test(a.href))
        .map(a => ({{href: a.href.split('?')[0], text: (a.textContent || '').trim().slice(0, 100)}}));
      const seen = new Set();
      const cards = p.filter(l => {{
        if (seen.has(l.href)) return false;
        seen.add(l.href); return true;
      }}).slice(0, {TOP_N});
      return cards.map((l, i) => {{
        const nm = l.href.match(/blog\\.naver\\.com\\/([a-zA-Z0-9_-]+)\\/(\\d+)/);
        const tm = l.href.match(/([a-zA-Z0-9_-]+)\\.tistory\\.com\\/(\\d+)/);
        return {{rank: i+1, id: nm ? nm[1] : (tm ? tm[1] : null), text: l.text}};
      }});
    }}
    """)


def measure_one(page, kw, blog_id):
    """한 키워드 실측 (Retry 포함). 반환: {kw, rank, extra_ranks?, title?, note?}"""
    url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&sm=tab_jum&query={quote_plus(kw)}"
    for attempt in range(1, MAX_RETRY + 1):
        try:
            page.goto(url, wait_until="networkidle", timeout=20000)
            time.sleep(random.uniform(1.0, 1.8))  # 랜덤 딜레이
            cards = parse_cards(page, blog_id)
            ours = [c for c in cards if c["id"] == blog_id]
            if ours:
                ranks = sorted(c["rank"] for c in ours)
                item = {"kw": kw, "rank": ranks[0]}
                if len(ranks) > 1: item["extra_ranks"] = ranks[1:]
                item["title"] = ours[0]["text"][:60]
                return item
            else:
                return {"kw": kw, "rank": None, "note": "권외"}
        except Exception as e:
            if attempt < MAX_RETRY:
                wait = 2 ** attempt  # 백오프: 2s, 4s
                print(f"    ⚠ retry {attempt}/{MAX_RETRY} ({e.__class__.__name__}) - {wait}s 대기")
                time.sleep(wait)
            else:
                return {"kw": kw, "rank": None, "note": f"실패({MAX_RETRY}회): {str(e)[:60]}"}


def measure_blog(blog_id, h):
    kws = collect_keywords(h, blog_id)
    if not kws:
        print(f"⚠ {blog_id}: 키워드 없음")
        return None
    print(f"\n📡 {blog_id}: {len(kws)}개 키워드 측정 시작")

    ua = random.choice(UA_LIST)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=ua, locale="ko-KR", viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for i, kw in enumerate(kws, 1):
            item = measure_one(page, kw, blog_id)
            results.append(item)
            if i % 50 == 0 or i == len(kws):
                hits5 = sum(1 for r in results if r.get("rank") and r["rank"] <= 5)
                print(f"  [{i}/{len(kws)}] 5위 안 {hits5}개")
        browser.close()

    return results


def main():
    if len(sys.argv) < 2:
        print("사용: measure_playwright.py <blog_id> [<blog_id> ...]"); sys.exit(1)

    targets = sys.argv[1:]
    h = json.load(open(HIST, encoding="utf-8"))
    import datetime
    today = datetime.date.today().isoformat()

    for bid in targets:
        results = measure_blog(bid, h)
        if not results: continue
        b = h["blogs"][bid]
        b.setdefault("keyword_rank", {})[today] = {
            "source": "playwright_실측",
            "items": results,
            "measured_at": datetime.datetime.now().isoformat(),
        }
        # 매 블로그 완료 시 저장 (job 중단되어도 부분 저장)
        json.dump(h, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        hits5 = sum(1 for r in results if r.get("rank") and r["rank"] <= 5)
        print(f"✅ {bid} 완료: {len(results)}개 · 5위 안 {hits5}개 · 저장 완료")


if __name__ == "__main__":
    main()
