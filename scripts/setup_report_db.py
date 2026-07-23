#!/usr/bin/env python3
"""'포스팅 주간 보고서' DB에 날짜(date) 속성 추가 + 기존 페이지 값 세팅 (원샷).

- '업로드일' (date) 속성 추가 (없으면)
- '상태' status 옵션에 '확인 전' 있는지 확인, 없으면 추가
- 이미 있는 페이지들에 업로드일=오늘, 상태=확인 전 세팅
"""
import os, sys, json, datetime
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"
TARGET_TITLE = "포스팅 주간 보고서"
NEW_DATE_KEY = "업로드일"

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
print(f"📋 data_source: {ds_id}")

# 3) 현재 스키마
ds = api(f"data_sources/{ds_id}")
props = ds.get("properties") or {}
print(f"현재 스키마 ({len(props)}개):")
for pk, pv in props.items():
    print(f"  - {pk} ({pv.get('type')})")

# 4) date 속성 없으면 추가
existing_date = next((k for k, v in props.items() if v.get("type") == "date"), None)
if existing_date:
    print(f"✅ date 속성 이미 존재: {existing_date!r}")
    date_key = existing_date
else:
    print(f"🆕 date 속성 추가: {NEW_DATE_KEY!r}")
    api(f"data_sources/{ds_id}", {
        "properties": {NEW_DATE_KEY: {"date": {}}}
    }, method="PATCH")
    date_key = NEW_DATE_KEY

# 5) status 속성 확인 + 옵션 확인
status_key = None
status_type = None
status_option = None
for pk, pv in props.items():
    t = pv.get("type")
    if t in ("select", "status") and ("진행" in pk or "상태" in pk or pk.lower() == "status"):
        status_key = pk
        status_type = t
        opts = (pv.get(t) or {}).get("options") or []
        print(f"✅ {t} 속성 '{pk}' 옵션:")
        for o in opts:
            print(f"    - {o['name']} ({o.get('color', '')})")
        # "확인 전" 우선, 없으면 첫 옵션
        pref = next((o["name"] for o in opts if "확인 전" in o["name"] or o["name"].strip() == "전"), None)
        status_option = pref or (opts[0]["name"] if opts else None)
        print(f"→ 세팅할 옵션: {status_option!r}")
        break

if not status_key:
    print("⚠ status/select 속성 없음 — 상태 세팅 스킵")

# 6) 기존 페이지 값 세팅
print("\n📝 기존 페이지 값 세팅:")
query = api(f"data_sources/{ds_id}/query", {"page_size": 100}, method="POST")
today = datetime.date.today().isoformat()
for p in query.get("results") or []:
    # 제목 조회
    title_text = ""
    for pk, pv in (p.get("properties") or {}).items():
        if pv.get("type") == "title":
            rich = pv.get("title") or []
            title_text = "".join(x.get("plain_text", "") for x in rich)
            break

    update_props = {}
    if date_key and (p.get("properties") or {}).get(date_key, {}).get("date") is None:
        update_props[date_key] = {"date": {"start": today}}
    if status_key and status_option:
        # status/select property 값 없으면 추가
        cur = (p.get("properties") or {}).get(status_key) or {}
        val = cur.get(status_type)
        if not val or not val.get("name"):
            update_props[status_key] = {status_type: {"name": status_option}}

    if not update_props:
        print(f"  • {title_text!r} — 이미 세팅됨, 스킵")
        continue

    try:
        api(f"pages/{p['id']}", {"properties": update_props}, method="PATCH")
        keys = list(update_props.keys())
        print(f"  ✅ {title_text!r} → {keys} 세팅")
    except Exception as ex:
        print(f"  ❌ {title_text!r} 실패: {ex}")

print("\n완료")
