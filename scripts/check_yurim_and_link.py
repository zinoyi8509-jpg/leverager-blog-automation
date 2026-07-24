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

# 1) 유림 페이지 및 하위 페이지 재귀 탐색 → DB 목록
print(f"=== 유림 페이지 트리 스캔 ===")
dbs = []  # (title, id, path)
def scan(block_id, path=""):
    cursor = None
    while True:
        p = f"blocks/{block_id}/children?page_size=100"
        if cursor: p += f"&start_cursor={cursor}"
        try:
            r = api(p)
        except Exception as ex:
            print(f"  ⚠ {path}: {ex}")
            return
        for b in r.get("results", []):
            t = b.get("type")
            if t == "child_database":
                title = (b.get("child_database") or {}).get("title") or "(무제)"
                full = f"{path}/{title}"
                print(f"  🗄  {full} · {b['id']}")
                dbs.append((title, b["id"], full))
            elif t == "child_page":
                title = (b.get("child_page") or {}).get("title") or ""
                print(f"  📄 {path}/{title}")
                scan(b["id"], f"{path}/{title}")
            elif t == "toggle":
                rich = (b.get("toggle") or {}).get("rich_text") or []
                text = "".join(x.get("plain_text", "") for x in rich)
                # 토글 안도 스캔
                scan(b["id"], f"{path}/🔽{text}")
        if not r.get("has_more"): break
        cursor = r.get("next_cursor")

scan(YURIM, "유림")

if not dbs:
    print("❌ 유림 페이지 트리에 DB 없음"); sys.exit(1)

# 2) 각 DB의 data_source 확인 (linked view에 필요)
print(f"\n=== DB 상세 ===")
for title, db_id in dbs:
    db_info = api(f"databases/{db_id}")
    for ds in db_info.get("data_sources") or []:
        print(f"  DB '{title}' → data_source {ds['id']} ({ds.get('name', '')})")

# 3) 확인만 하고 링크 삽입은 스킵 (사용자 확인 후 별도 실행)
print(f"\n=== 발견된 DB 목록 (링크 삽입은 다음 단계) ===")
for title, db_id, path in dbs:
    print(f"  · {title} ({path})")
    print(f"    id={db_id}")
print(f"\n확인 후 어떤 DB를 링크할지 결정 후 다음 단계 실행")

