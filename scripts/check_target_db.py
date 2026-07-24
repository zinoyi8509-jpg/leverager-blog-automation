#!/usr/bin/env python3
"""대상 DB 스키마 확인 (Google Calendar 동기화용)."""
import os, json, urllib.request

TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
if not TOKEN: print("❌ NOTION_TOKEN 필요"); exit(1)

DB_ID = "3a761e2336fd80fb9f9ef20b1eddfa1f"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2025-09-03"}

def get(path):
    req = urllib.request.Request(f"https://api.notion.com/v1/{path}", headers=H, method="GET")
    return json.loads(urllib.request.urlopen(req).read())

# DB 정보
db = get(f"databases/{DB_ID}")
title = "".join(x.get("plain_text", "") for x in (db.get("title") or []))
print(f"📚 DB: {title!r}")
print(f"parent: {db.get('parent')}")

# data_sources
for ds in db.get("data_sources") or []:
    ds_id = ds["id"]
    print(f"\n📋 data_source: {ds_id}")
    full = get(f"data_sources/{ds_id}")
    props = full.get("properties") or {}
    print(f"properties ({len(props)}개):")
    for pk, pv in props.items():
        t = pv.get("type")
        extra = ""
        if t == "select":
            opts = (pv.get("select") or {}).get("options") or []
            extra = f" [{', '.join(o['name'] for o in opts)}]"
        elif t == "status":
            opts = (pv.get("status") or {}).get("options") or []
            extra = f" [{', '.join(o['name'] for o in opts)}]"
        print(f"  · {pk} ({t}){extra}")

    # 최근 항목 3개
    body = {"page_size": 3}
    req = urllib.request.Request(
        f"https://api.notion.com/v1/data_sources/{ds_id}/query",
        data=json.dumps(body).encode(),
        headers={**H, "Content-Type": "application/json"},
        method="POST",
    )
    pages = json.loads(urllib.request.urlopen(req).read())
    print(f"\n최근 페이지 {len(pages.get('results') or [])}개:")
    for p in pages.get("results") or []:
        for pk, pv in (p.get("properties") or {}).items():
            if pv.get("type") == "title":
                rich = pv.get("title") or []
                t = "".join(x.get("plain_text", "") for x in rich)
                print(f"  • {t!r}")
                break
