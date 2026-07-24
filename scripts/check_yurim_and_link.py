#!/usr/bin/env python3
"""유림 페이지의 캘린더 DB 확인 + 주간 보고서 페이지에 링크된 뷰 삽입.

원본: 유림 페이지 (28c61e2336fd805b9a4bdf45a9b52a9f) 캘린더 DB
대상: 주간 보고서 페이지 (3a661e2336fd8041abdac15972e10e14)
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
YURIM = "28c61e2336fd805b9a4bdf45a9b52a9f"
TARGET = "3a661e2336fd8041abdac15972e10e14"

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
        err = e.read().decode('utf-8', errors='replace')
        print(f"❌ {e.code}: {err[:500]}")
        raise

# 1) 유림 페이지의 DB들 조회
print(f"=== 유림 페이지 하위 블록 ===")
resp = api(f"blocks/{YURIM}/children?page_size=100")
dbs = []
for b in resp.get("results", []):
    t = b.get("type")
    if t == "child_database":
        title = (b.get("child_database") or {}).get("title") or "(무제)"
        print(f"  🗄  {title} · {b['id']}")
        dbs.append((title, b["id"]))
    elif t == "child_page":
        title = (b.get("child_page") or {}).get("title") or ""
        print(f"  📄 page: {title}")
    else:
        print(f"  ▪ {t}")

if not dbs:
    print("❌ 유림 페이지에 DB 없음"); sys.exit(1)

# 2) 각 DB의 data_source 확인 (linked view에 필요)
print(f"\n=== DB 상세 ===")
for title, db_id in dbs:
    db_info = api(f"databases/{db_id}")
    for ds in db_info.get("data_sources") or []:
        print(f"  DB '{title}' → data_source {ds['id']} ({ds.get('name', '')})")

# 3) 대상 페이지에 link_to_page 블록 추가 (Notion API로 가능한 링크 방식)
# 각 DB마다 link_to_page 블록 삽입
print(f"\n=== 대상 페이지에 링크 추가 ===")
children = []
for title, db_id in dbs:
    children.append({
        "object": "block",
        "type": "link_to_page",
        "link_to_page": {
            "type": "database_id",
            "database_id": db_id,
        }
    })

resp = api(f"blocks/{TARGET}/children", {"children": children}, method="PATCH")
for i, b in enumerate(resp.get("results", [])):
    print(f"  ✅ 링크 삽입 완료: {dbs[i][0]} · block={b['id']}")

print("\n완료. 노션에서 확인하세요.")
print("참고: link_to_page는 페이지 링크 형태로 표시됨. 인라인 캘린더 뷰가 필요하면")
print("      노션 UI에서 그 링크 우클릭 → '전환' → '링크된 데이터베이스로 전환' 필요할 수 있음.")
