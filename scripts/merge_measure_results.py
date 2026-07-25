#!/usr/bin/env python3
"""각 measure job이 남긴 artifact들을 병합해 최종 history.json 생성.

artifacts/rank-A/history.json (그룹 A가 측정한 결과)
artifacts/rank-B/history.json (그룹 B가 측정한 결과)
... → 각 그룹이 담당한 블로그의 keyword_rank 만 병합
"""
import os, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "data", "history.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # 기준 history.json (레포지토리의 최신)
    h = load(BASE)
    today_paths = sorted(glob.glob(os.path.join(ROOT, "artifacts", "rank-*", "history.json")))
    print(f"발견된 artifact: {len(today_paths)}개")

    total_updated = 0
    for p in today_paths:
        art = load(p)
        for bid, ab in (art.get("blogs") or {}).items():
            art_kr = ab.get("keyword_rank") or {}
            if not art_kr: continue
            # 각 그룹은 자기 담당 블로그만 keyword_rank를 새로 채웠음
            base_b = h["blogs"].setdefault(bid, {})
            base_kr = base_b.setdefault("keyword_rank", {})
            for date, rec in art_kr.items():
                if date not in base_kr or rec.get("source") == "playwright_실측":
                    base_kr[date] = rec
                    total_updated += 1
            # published/daily 등은 원본 유지 (실측만 병합)

    with open(BASE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)
    print(f"✅ 병합 완료: {total_updated}개 blog×date keyword_rank 갱신")


if __name__ == "__main__":
    main()
