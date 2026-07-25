#!/usr/bin/env python3
"""네이버 블로그 RSS로 발행글 자동 수집.

각 블로그의 RSS 피드에서 최근 발행글을 파싱해 history.json의 published에 누적.
유림 업무보고 없이도 자동으로 blogs.*.published가 채워짐.

RSS URL: https://rss.blog.naver.com/{blog_id}.xml

사용:
  python3 scripts/naver_rss_ingest.py            # 전 채널
  python3 scripts/naver_rss_ingest.py sh33391    # 특정 채널만
"""
import os, sys, json, re, urllib.request
from datetime import datetime
from html import unescape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HIST = os.path.join(ROOT, "data", "history.json")

# 자동 RSS 수집 대상 (전체 11개 네이버 블로그)
TARGETS = [
    "leverager_solution",    # 레솔
    "cdo2795",               # 건테리어
    "cdo27951",              # 건테리어주택
    "cdo27952",              # 건테리어스
    "cdo27953",              # 메카(건축사)
    "chanwoo0919",           # 마실
    "kbtax0503",             # 다원
    "cowper7710",            # 카우퍼
    "sh33391",               # 서휘
    "shingonggandesign02",   # 신공간
    "kkomkkomcleaning",      # 꼼꼼
]


def fetch_rss(blog_id, timeout=15):
    """네이버 블로그 RSS 파싱 → [(date, title), ...] 반환"""
    url = f"https://rss.blog.naver.com/{blog_id}.xml"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            xml = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ❌ RSS 실패 {blog_id}: {e}")
        return []

    items = []
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.DOTALL):
        block = m.group(1)
        title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        pub_m = re.search(r"<pubDate>(.*?)</pubDate>", block)
        if not (title_m and pub_m): continue
        title = unescape(title_m.group(1).strip())
        try:
            dt = datetime.strptime(pub_m.group(1).strip(), "%a, %d %b %Y %H:%M:%S %z")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
        items.append((date_str, title))
    return items


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    targets = args if args else TARGETS

    h = json.load(open(HIST, encoding="utf-8"))
    total_new = 0

    for bid in targets:
        b = h["blogs"].get(bid)
        if not b:
            print(f"⚠ {bid} 없음 (blogs에 등록되지 않음)")
            continue
        items = fetch_rss(bid)
        if not items:
            print(f"  {bid}: RSS 결과 없음")
            continue

        published = b.setdefault("published", {})
        new_cnt = 0
        for date, title in items:
            titles_on_date = published.setdefault(date, [])
            if not any((x.get("t") or "").strip() == title for x in titles_on_date):
                titles_on_date.append({"t": title})
                new_cnt += 1
        total_new += new_cnt
        print(f"  ✅ {bid}: {len(items)}개 RSS 조회 · 신규 {new_cnt}개 (총 {sum(len(v) for v in published.values())}개)")

    json.dump(h, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n총 신규 발행글: {total_new}개 (published 누적)")


if __name__ == "__main__":
    main()
