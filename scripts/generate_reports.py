#!/usr/bin/env python3
"""각 회사 최신 측정 결과 요약 출력 (GitHub Actions 로그용)"""
import json
from pathlib import Path

HIST = Path(__file__).resolve().parent.parent / "data" / "history.json"
h = json.load(open(HIST, encoding="utf-8"))

print("=" * 60)
print("📊 각 회사 최신 measurement 요약")
print("=" * 60)
for bid, b in h.get("blogs", {}).items():
    kr = b.get("keyword_rank", {})
    dates = sorted([d for d in kr if (kr[d] or {}).get("source") == "playwright_실측"], reverse=True)
    if not dates: continue
    d = dates[0]
    items = kr[d].get("items", [])
    p1 = sum(1 for it in items if it.get("rank") and it["rank"] <= 10)
    ranks = [it["rank"] for it in items if it.get("rank")]
    avg = round(sum(ranks)/len(ranks), 2) if ranks else "-"
    pct = f"({p1*100//len(items) if items else 0}%)" if items else ""
    print(f"  {bid:22s} 측정 {len(items):3d} · 1페이지 {p1:3d} {pct:>6s} · 평균 {avg}위 [{d}]")
