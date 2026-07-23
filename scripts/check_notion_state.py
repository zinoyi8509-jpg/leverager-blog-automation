#!/usr/bin/env python3
"""주간 보고서 페이지의 현재 구조/DB/스키마 확인 (원샷 진단)."""
import os, sys, json
import urllib.request

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"

if not TOKEN: print("❌ NOTION_TOKEN 필요"); sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
}

def get(path):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        headers=HEADERS, method="GET",
    )
    return json.loads(urllib.request.urlopen(req).read())


print("=" * 60)
print("📄 부모 페이지 자식 블록 목록")
print("=" * 60)

resp = get(f"blocks/{PARENT}/children?page_size=100")
databases = []
for b in resp.get("results", []):
    t = b.get("type")
    if t == "child_database":
        title = (b.get("child_database") or {}).get("title") or "(무제)"
        print(f"  🗄  child_database: {title} · {b['id']}")
        databases.append((title, b["id"]))
    elif t == "child_page":
        title = (b.get("child_page") or {}).get("title") or "(무제)"
        print(f"  📄 child_page: {title} · {b['id']}")
    elif t == "toggle":
        rich = (b.get("toggle") or {}).get("rich_text") or []
        text = "".join(x.get("plain_text", "") for x in rich)
        print(f"  🔽 toggle: {text!r} · {b['id']}")
    elif t == "paragraph":
        rich = (b.get("paragraph") or {}).get("rich_text") or []
        text = "".join(x.get("plain_text", "") for x in rich)
        if text.strip():
            print(f"  📝 paragraph: {text[:50]!r}")
    else:
        print(f"  ▪ {t}")

# 각 DB의 스키마
for title, db_id in databases:
    print()
    print(f"=" * 60)
    print(f"🗄  DB 상세: {title}")
    print(f"=" * 60)
    db_info = get(f"databases/{db_id}")
    for ds in db_info.get("data_sources") or []:
        ds_id = ds["id"]
        ds_name = ds.get("name") or "(무제)"
        print(f"  data_source: {ds_name} · {ds_id}")
        full = get(f"data_sources/{ds_id}")
        props = full.get("properties") or {}
        print(f"  properties ({len(props)}개):")
        for pk, pv in props.items():
            ptype = pv.get("type")
            extra = ""
            if ptype == "select":
                opts = (pv.get("select") or {}).get("options") or []
                extra = f" [옵션: {', '.join(o['name'] for o in opts)}]"
            print(f"    - {pk} ({ptype}){extra}")

        # 최근 페이지 3개 (2025-09-03 API로 data_source query)
        try:
            body = {"page_size": 5}
            req = urllib.request.Request(
                f"https://api.notion.com/v1/data_sources/{ds_id}/query",
                data=json.dumps(body).encode(),
                headers={**HEADERS, "Content-Type": "application/json"},
                method="POST",
            )
            pages = json.loads(urllib.request.urlopen(req).read())
            results = pages.get("results") or []
            print(f"  최근 페이지 ({len(results)}개):")
            for p in results:
                title_prop = None
                for pk, pv in (p.get("properties") or {}).items():
                    if pv.get("type") == "title":
                        rich = pv.get("title") or []
                        title_prop = "".join(x.get("plain_text", "") for x in rich)
                        break
                print(f"    • {title_prop!r}")
        except Exception as ex:
            print(f"  ⚠ 페이지 조회 실패: {ex}")

print()
print("=" * 60)
print("완료")
