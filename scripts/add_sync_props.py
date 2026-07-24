#!/usr/bin/env python3
"""'새 데이터베이스'에 GCal Event ID + 마지막 동기화 속성 추가."""
import os, json, urllib.request, urllib.error

TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
if not TOKEN: print("❌ NOTION_TOKEN 필요"); exit(1)

DS_ID = "3a761e23-36fd-804d-b15b-000b7d5b2443"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2025-09-03",
     "Content-Type": "application/json"}

def api(path, body, method="PATCH"):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(body).encode(),
        headers=H, method=method,
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"❌ {e.code}: {e.read().decode()[:400]}")
        raise

resp = api(f"data_sources/{DS_ID}", {
    "properties": {
        "GCal Event ID": {"rich_text": {}},
        "마지막 동기화": {"date": {}},
    }
})
print("✅ 속성 추가 완료: GCal Event ID (rich_text), 마지막 동기화 (date)")
