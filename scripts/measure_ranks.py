#!/usr/bin/env python3
"""
네이버 블로그탭 실제 순위 측정 (Playwright 헤드리스).

윤팀장 수기 측정과 별개로, 실제 네이버 검색 결과를 그대로 추출.
API sim ≠ 수기 ≠ 실제 — Playwright가 가장 진짜에 가까움.

비용: 0원 (헤드리스 Chromium 로컬 실행)
시간: 키워드당 약 3~5초 (53개면 약 3~5분)

사용:
  python3 dashboards/scripts/keyword_realrank_playwright.py
  python3 dashboards/scripts/keyword_realrank_playwright.py masil  # 특정 회사만
  python3 dashboards/scripts/keyword_realrank_playwright.py cowper mecca

적재:
  blogs.{naverId}.keyword_rank.{YYYY-MM-DD}
    source: "playwright_실측"
    items: [{kw, rank, extra_ranks, title}, ...]
"""
import sys, os, json, datetime, time
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HIST = os.path.join(ROOT, "data", "history.json")

# 회사 → 네이버 블로그 ID 매핑
CLIENTS = {
    "masil":  "chanwoo0919",
    "cowper": "cowper7710",
    "mecca":  "cdo27953",
    "dawon":  "kbtax0503",
    "seohwi": "sh33391",             # 서휘 (건축)
    "shingonggan": "shingonggandesign02",  # 신공간 (인테리어)
    "gunterior": "cdo2795",          # 건테리어 (자체)
    "gunteriors": "cdo27952",        # 건테리어스 (자체)
    "gunterior_house": "cdo27951",   # 건테리어주택 (자체)
    "leso": "leverager_solution",    # 레솔 (자체)
    "kkomkkom": "kkomkkomcleaning",  # 꼼꼼종합클린 (자체)
}
OUR_IDS = set(CLIENTS.values()) | {
    "cdo2795", "cdo27952", "cdo27951",  # 건테리어/건테리어스/건테리어주택
    "kbtax0503", "leverager_solution",  # 다원/레솔
    "kkomkkomcleaning",  # 꼼꼼종합클린
}

# 한 페이지에서 최대 몇 위까지 측정할지
TOP_N = 30


def extract_ranks(page):
    """현재 페이지에서 블로그 글 카드 순위 추출"""
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


def search_keyword(page, kw, double_check=True):
    """한 키워드 검색 → 우리 채널 글의 순위 추출.

    더블체크 룰 (절대 오류 방지):
    1차: sleep 1.2초 + networkidle — 충분히 로드 대기
    권외 나오면 2차 재측정: sleep 2.0초 + 한 번 더 확인
    두 번 다 권외인 경우만 진짜 권외로 확정
    """
    # 중요: sm=tab_jum 필수 — 자연 검색 흐름(naver.com -> 검색 -> 블로그탭 클릭) URL.
    # sm 없으면 마실/전 회사에 유리한 비정상 알고리즘 결과 반환 (2026-06-30 발견).
    url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&sm=tab_jum&query={quote_plus(kw)}"
    page.goto(url, wait_until="networkidle", timeout=20000)
    time.sleep(1.2)
    cards = extract_ranks(page)
    ours = [c for c in cards if c["id"] in OUR_IDS]

    # 권외(자사 글 없음)면 즉시 2차 재측정 — 더블체크 강제
    if not ours and double_check:
        time.sleep(1.0)
        page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(2.0)  # 더 길게 대기
        cards = extract_ranks(page)
        ours = [c for c in cards if c["id"] in OUR_IDS]

    by_id = {}
    for c in ours:
        by_id.setdefault(c["id"], []).append(c)
    return by_id, cards


def get_manual_keywords(h, naver_id):
    """history.json에서 해당 블로그의 수기 측정 키워드 가져오기"""
    kr = h["blogs"][naver_id].get("keyword_rank", {})
    manual = {d: v for d, v in kr.items() if (v or {}).get("source") == "수기"}
    if not manual:
        return []
    latest = sorted(manual)[-1]
    items = manual[latest].get("items", [])
    return [it["kw"] for it in items]


def main():
    args = [a for a in sys.argv[1:] if a in CLIENTS]
    targets = args if args else list(CLIENTS.keys())
    today = datetime.date.today().isoformat()

    h = json.load(open(HIST, encoding="utf-8"))

    # 모든 키워드 수집
    all_jobs = []  # (kw, [naver_id, ...])
    seen_kws = {}
    for client_id in targets:
        nv = CLIENTS[client_id]
        for kw in get_manual_keywords(h, nv):
            if kw not in seen_kws:
                seen_kws[kw] = [nv]
            elif nv not in seen_kws[kw]:
                seen_kws[kw].append(nv)
    all_jobs = list(seen_kws.items())
    print(f"📡 측정 대상: {len(all_jobs)}개 키워드 ({len(targets)}개 회사)")

    # 채널별 적재 데이터 누적
    bucket = {nv: [] for nv in CLIENTS.values()}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        for i, (kw, naver_ids) in enumerate(all_jobs, 1):
            try:
                by_id, _ = search_keyword(page, kw)
                # 해당 키워드를 측정한 채널들에 결과 기록
                for nv in naver_ids:
                    cards = by_id.get(nv, [])
                    if cards:
                        ranks = sorted(c["rank"] for c in cards)
                        item = {"kw": kw, "rank": ranks[0]}
                        if len(ranks) > 1:
                            item["extra_ranks"] = ranks[1:]
                        item["title"] = cards[0]["text"][:60]
                    else:
                        item = {"kw": kw, "rank": None, "note": "권외(30위 밖)"}
                    bucket[nv].append(item)
                # 진행 상황
                hits = sum(len(v) for v in by_id.values())
                hit_ids = ",".join(by_id.keys()) if by_id else "권외"
                print(f"  [{i}/{len(all_jobs)}] {kw}: {hit_ids}")
            except Exception as ex:
                print(f"  [{i}/{len(all_jobs)}] {kw}: ⚠ 실패 {ex}")
                for nv in naver_ids:
                    bucket[nv].append({"kw": kw, "rank": None, "note": f"오류: {ex}"})

        browser.close()

    # history.json 적재
    for nv, items in bucket.items():
        if items:
            h["blogs"][nv]["keyword_rank"][today] = {
                "source": "playwright_실측",
                "items": items,
                "measured_by": "Playwright headless",
            }
    with open(HIST, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

    # 결과 요약
    print()
    print("=" * 60)
    print(f"✅ 적재 완료 (source=playwright_실측, 일자={today})")
    for nv, items in bucket.items():
        if not items:
            continue
        in_p1 = sum(1 for it in items if it.get("rank") and it["rank"] <= 10)
        in_p2 = sum(1 for it in items if it.get("rank") and 11 <= it["rank"] <= 30)
        out = sum(1 for it in items if not it.get("rank"))
        ranks = [it["rank"] for it in items if it.get("rank")]
        avg = round(sum(ranks)/len(ranks), 2) if ranks else None
        print(f"  {nv}: 측정 {len(items)} / 1페이지 {in_p1} / 2~3페이지 {in_p2} / 권외 {out} / 평균 {avg}위")


if __name__ == "__main__":
    main()
