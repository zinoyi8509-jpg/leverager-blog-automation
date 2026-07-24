#!/usr/bin/env python3
"""원본 캘린더 DB를 주간 보고서 페이지에 최대한 자동으로 링크.
Notion API 제약: 인라인 DB는 linked view 자동 생성 불가.
→ 대신 database mention (클릭 시 원본 이동)을 삽입.
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
SOURCE_DB = "28c61e2336fd811eb1f1f00ff5e29654"
TARGET_PAGE = "3a661e2336fd8041abdac15972e10e14"
SOURCE_URL = "https://www.notion.so/28c61e2336fd811eb1f1f00ff5e29654"

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
        print(f"  ⚠ {e.code}: {err[:300]}")
        raise

# 원본 DB 확인
db = api(f"databases/{SOURCE_DB}")
db_title = "".join(x.get("plain_text", "") for x in (db.get("title") or [])) or "(무제)"
print(f"📚 원본 DB: {db_title!r}")

# === 시도 1: database mention (inline 텍스트 링크) ===
print("\n시도 1: database mention 삽입...")
try:
    resp = api(f"blocks/{TARGET_PAGE}/children", {
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📅 원본 캘린더"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "원본 DB 열기 → "}},
                        {
                            "type": "mention",
                            "mention": {
                                "type": "database",
                                "database": {"id": SOURCE_DB}
                            }
                        }
                    ]
                }
            }
        ]
    }, method="PATCH")
    for b in resp.get("results", []):
        print(f"  ✅ {b.get('type')} 삽입: {b['id']}")
    print("→ database mention 성공 (텍스트 링크 형태)")
except Exception:
    print("→ mention 실패")

# === 시도 2: 원본 DB의 부모 페이지 링크 ===
print("\n시도 2: 원본 DB의 부모 페이지 링크...")
try:
    parent = db.get("parent") or {}
    if parent.get("type") == "page_id":
        parent_id = parent["page_id"]
        print(f"  원본 DB의 부모 페이지: {parent_id}")
        api(f"blocks/{TARGET_PAGE}/children", {
            "children": [
                {
                    "object": "block",
                    "type": "link_to_page",
                    "link_to_page": {"type": "page_id", "page_id": parent_id}
                }
            ]
        }, method="PATCH")
        print("  ✅ 부모 페이지 링크 추가됨 (그 안에 원본 캘린더 있음)")
    else:
        print(f"  부모 타입={parent.get('type')} — 페이지 아님, 스킵")
except Exception:
    print("  → 실패")

# === 시도 3: URL 하이퍼링크 (fallback) ===
print("\n시도 3: URL bookmark 삽입...")
try:
    api(f"blocks/{TARGET_PAGE}/children", {
        "children": [
            {
                "object": "block",
                "type": "bookmark",
                "bookmark": {
                    "url": SOURCE_URL,
                    "caption": [{"type": "text", "text": {"content": f"원본 캘린더: {db_title}"}}]
                }
            }
        ]
    }, method="PATCH")
    print("  ✅ bookmark 카드 추가됨")
except Exception:
    print("  → 실패")

print("\n=== 완료 ===")
print("주간 보고서 페이지에 원본 캘린더 접근 링크 3종 삽입:")
print("  1. Heading + database mention (텍스트 내 링크)")
print("  2. 원본 페이지 카드 링크")
print("  3. Bookmark 카드")
print(f"\n👉 노션 페이지 확인: https://www.notion.so/{TARGET_PAGE.replace('-','')}")
print("불필요한 것은 노션 UI에서 지우세요.")
