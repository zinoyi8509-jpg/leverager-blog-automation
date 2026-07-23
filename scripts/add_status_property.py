#!/usr/bin/env python3
"""부모 페이지 아래 첫 데이터베이스에 '진행상태' select property 추가 (원샷).
옵션: 확인 전 (red) / 확인완료 (green)
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"

if not TOKEN:
    print("❌ NOTION_TOKEN 필요"); sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}

def api(path, body=None, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data, headers=HEADERS, method=method,
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"❌ {e.code}: {e.read().decode('utf-8', errors='replace')[:600]}")
        raise


# 부모 페이지 아래 첫 DB 찾기
cursor = None
db_id = None
while True:
    path = f"blocks/{PARENT}/children?page_size=100"
    if cursor:
        path += f"&start_cursor={cursor}"
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        headers=HEADERS, method="GET",
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    for b in resp.get("results", []):
        if b.get("type") == "child_database":
            db_id = b["id"]
            title = (b.get("child_database") or {}).get("title") or "(무제)"
            print(f"📚 DB 발견: {title} · {db_id}")
            break
    if db_id or not resp.get("has_more"):
        break
    cursor = resp.get("next_cursor")

if not db_id:
    print("❌ 데이터베이스 없음"); sys.exit(1)

# data_source_id 조회
db_info = api(f"databases/{db_id}", method="GET")
sources = db_info.get("data_sources") or []
if not sources:
    print("❌ data_source 없음"); sys.exit(1)
ds_id = sources[0]["id"]
print(f"📋 data_source: {ds_id}")

# 현재 스키마 조회
ds = api(f"data_sources/{ds_id}", method="GET")
props = ds.get("properties") or {}
if "진행상태" in props:
    print("⚠ '진행상태' property 이미 존재 — 스킵")
    sys.exit(0)

# 진행상태 select property 추가
resp = api(f"data_sources/{ds_id}", {
    "properties": {
        "진행상태": {
            "select": {
                "options": [
                    {"name": "확인 전", "color": "red"},
                    {"name": "확인완료", "color": "green"},
                ]
            }
        }
    }
}, method="PATCH")
print(f"✅ '진행상태' property 추가 완료 (확인 전 / 확인완료)")
