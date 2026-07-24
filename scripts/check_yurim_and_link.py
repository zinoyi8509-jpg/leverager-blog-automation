#!/usr/bin/env python3
"""사용자가 지정한 원본 캘린더 DB를 주간 보고서 페이지에 링크 (원샷).

원본 DB: 28c61e2336fd811eb1f1f00ff5e29654 (사용자가 URL로 전달)
대상 페이지: 3a661e2336fd8041abdac15972e10e14 (주간 보고서)
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
SOURCE_DB = "28c61e2336fd811eb1f1f00ff5e29654"
TARGET_PAGE = "3a661e2336fd8041abdac15972e10e14"

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
        print(f"❌ {e.code}: {err[:600]}")
        raise

# 1) 원본 DB 확인
print(f"=== 원본 DB 조회 ===")
db_info = api(f"databases/{SOURCE_DB}")
title_rich = db_info.get("title") or []
db_title = "".join(x.get("plain_text", "") for x in title_rich) or "(무제)"
print(f"  📚 DB: {db_title!r}")

# data_source 정보
for ds in db_info.get("data_sources") or []:
    ds_id = ds["id"]
    ds_name = ds.get("name", "")
    print(f"  📋 data_source: {ds_id} ({ds_name})")

    # properties 스키마
    full = api(f"data_sources/{ds_id}")
    props = full.get("properties") or {}
    print(f"  properties ({len(props)}개):")
    for pk, pv in props.items():
        print(f"    - {pk} ({pv.get('type')})")

# 2) 주간 보고서 페이지에 link_to_page 블록 추가
print(f"\n=== 주간 보고서 페이지에 링크 삽입 ===")
resp = api(f"blocks/{TARGET_PAGE}/children", {
    "children": [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "📅 캘린더 (원본 링크): "}, "annotations": {"bold": True}}
                ]
            }
        },
        {
            "object": "block",
            "type": "link_to_page",
            "link_to_page": {
                "type": "database_id",
                "database_id": SOURCE_DB,
            }
        }
    ]
}, method="PATCH")

for b in resp.get("results", []):
    print(f"  ✅ 블록 삽입: {b.get('type')} · {b['id']}")

print(f"\n✅ 완료")
print(f"\n⚠ 참고: link_to_page 는 링크 카드 형태로 표시됨.")
print(f"   노션 UI에서 그 링크를 인라인 캘린더로 표시하려면:")
print(f"   1. 삽입된 링크 블록 옆 ⋮⋮ 핸들 클릭")
print(f"   2. '전환' → '링크된 데이터베이스로 전환' 선택")
print(f"   3. 뷰 유형을 '캘린더'로 변경")
