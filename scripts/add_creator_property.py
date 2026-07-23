#!/usr/bin/env python3
"""'블로그 포스팅' DB에 '작성자' (created_by) 속성 자동 추가 (원샷).
매 페이지 생성 시 노션 계정 기반으로 자동 세팅됨. 수정 불가.
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"
TARGET_TITLE = "블로그 포스팅"
NEW_PROP = "작성자"

if not TOKEN: print("❌ NOTION_TOKEN 필요"); sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
}

def api(path, body=None, method="GET"):
    data = json.dumps(body).encode() if body is not None else None
    h = dict(HEADERS)
    if data: h["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data, headers=h, method=method,
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"❌ {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")
        raise

# 1) 대상 DB 찾기
resp = api(f"blocks/{PARENT}/children?page_size=100")
db_id = None
for b in resp.get("results", []):
    if b.get("type") == "child_database":
        title = (b.get("child_database") or {}).get("title") or ""
        if title.strip() == TARGET_TITLE:
            db_id = b["id"]
            print(f"📚 DB 발견: {title!r} · {db_id}")
            break

if not db_id:
    print(f"❌ '{TARGET_TITLE}' DB 못 찾음"); sys.exit(1)

# 2) data_source_id
db_info = api(f"databases/{db_id}")
ds_id = (db_info.get("data_sources") or [{}])[0].get("id")

# 3) 현재 스키마
ds = api(f"data_sources/{ds_id}")
props = ds.get("properties") or {}
print(f"현재 스키마 ({len(props)}개):")
for pk, pv in props.items():
    print(f"  - {pk} ({pv.get('type')})")

# 4) created_by 속성 이미 있는지 확인
exists = next((k for k, v in props.items() if v.get("type") == "created_by"), None)
if exists:
    print(f"✅ created_by 속성 이미 존재: {exists!r}")
    sys.exit(0)

# 5) 추가
print(f"🆕 '{NEW_PROP}' (created_by) 속성 추가")
api(f"data_sources/{ds_id}", {
    "properties": {NEW_PROP: {"created_by": {}}}
}, method="PATCH")
print(f"✅ 완료")
