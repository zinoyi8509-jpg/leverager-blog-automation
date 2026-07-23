#!/usr/bin/env python3
"""노션 데이터베이스에 주간 윤팀장 보고서 항목 추가 + PDF 파일 직접 첨부.
부모 페이지 아래 인라인 데이터베이스 자동 생성/재사용 → 최신순 정렬 유지.
"""
import os, sys, json, datetime, mimetypes
import urllib.request, urllib.error
from pathlib import Path

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"  # 주간 보고서 (레버리저 팀)

if not TOKEN:
    print("❌ NOTION_TOKEN 필요"); sys.exit(1)

NOTION_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
}

def notion(path, body=None, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data,
        headers={**NOTION_HEADERS, "Content-Type": "application/json"},
        method=method,
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"❌ Notion API {e.code}: {err_body[:600]}")
        raise

def rt(text, bold=False):
    return [{"type": "text", "text": {"content": text}, "annotations": {"bold": bold}}]

def paragraph(text, bold=False):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": rt(text, bold)}}

def heading(text, level=2):
    return {"object": "block", "type": f"heading_{level}",
            f"heading_{level}": {"rich_text": rt(text)}}

def upload_file(pdf_path: Path):
    """Notion File Upload API로 파일 업로드 → upload_id 반환."""
    init = notion("file_uploads", {
        "filename": pdf_path.name,
        "content_type": "application/pdf",
    })
    upload_id = init["id"]
    boundary = "----NotionBoundary" + upload_id[:8]
    data = pdf_path.read_bytes()
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n'
        f'Content-Type: application/pdf\r\n\r\n'
    ).encode() + data + f'\r\n--{boundary}--\r\n'.encode()

    req = urllib.request.Request(
        f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
        data=body,
        headers={
            **NOTION_HEADERS,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return upload_id


def file_block(upload_id, caption):
    return {
        "object": "block",
        "type": "file",
        "file": {
            "type": "file_upload",
            "file_upload": {"id": upload_id},
            "caption": rt(caption),
        },
    }


DB_TITLE = "포스팅 주간 보고서"  # 사용자가 만든 DB 이름 (앞뒤 공백 무시 매칭)


def get_data_source_id(database_id):
    """DB id → 첫 번째 data_source_id (2025-09-03 API)."""
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{database_id}",
        headers=NOTION_HEADERS,
        method="GET",
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    sources = resp.get("data_sources") or []
    if not sources:
        raise RuntimeError(f"DB {database_id} 에 data_sources 없음")
    return sources[0]["id"]


def get_data_source_schema(data_source_id):
    """data_source의 properties 스키마 조회 → title/date/status 자동 감지.
    status는 select 또는 status 타입 모두 지원. 반환: (title_key, date_key, status_info)
    status_info: (key, type, first_option_name) or None"""
    req = urllib.request.Request(
        f"https://api.notion.com/v1/data_sources/{data_source_id}",
        headers=NOTION_HEADERS,
        method="GET",
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    props = resp.get("properties") or {}
    title_key = next((k for k, v in props.items() if v.get("type") == "title"), None)
    date_key = next((k for k, v in props.items() if v.get("type") == "date"), None)

    status_info = None
    for k, v in props.items():
        t = v.get("type")
        if t not in ("select", "status"): continue
        if not ("진행" in k or "상태" in k or k.lower() == "status"): continue
        opts = (v.get(t) or {}).get("options") or []
        # "확인 전"이 있으면 그것, 아니면 첫 번째 옵션
        preferred = next((o["name"] for o in opts if "확인 전" in o["name"] or "미확인" in o["name"] or "전" == o["name"]), None)
        first_opt = preferred or (opts[0]["name"] if opts else None)
        if first_opt:
            status_info = (k, t, first_opt)
        break
    return title_key, date_key, status_info


def find_or_create_database():
    """부모 페이지 아래에서 DB_TITLE 일치하는 DB 찾기 (앞뒤 공백 무시).
    없으면 아무 DB나 첫 것 재사용, 그것도 없으면 새로 생성. → data_source_id 반환."""
    cursor = None
    all_dbs = []  # (title, id)
    while True:
        path = f"blocks/{PARENT}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        req = urllib.request.Request(
            f"https://api.notion.com/v1/{path}",
            headers=NOTION_HEADERS,
            method="GET",
        )
        resp = json.loads(urllib.request.urlopen(req).read())
        for b in resp.get("results", []):
            if b.get("type") == "child_database":
                title = (b.get("child_database") or {}).get("title") or "(무제)"
                all_dbs.append((title, b["id"]))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    # 1) 이름 일치(공백 무시) 우선
    for title, bid in all_dbs:
        if title.strip() == DB_TITLE.strip():
            print(f"  📚 이름 매칭 DB 재사용: {title!r} · {bid}")
            return get_data_source_id(bid)

    # 2) 이름 안 맞아도 첫 DB fallback
    if all_dbs:
        title, bid = all_dbs[0]
        print(f"  📚 첫 DB fallback: {title!r} · {bid}")
        return get_data_source_id(bid)

    # 3) DB 아예 없으면 새로 생성
    print("  🆕 데이터베이스 신규 생성")
    db = notion("databases", {
        "parent": {"type": "page_id", "page_id": PARENT},
        "is_inline": True,
        "title": rt(DB_TITLE),
        "properties": {
            "제목": {"title": {}},
            "보고 날짜": {"date": {}},
        },
    })
    sources = db.get("data_sources") or []
    if sources:
        return sources[0]["id"]
    return get_data_source_id(db["id"])


CLIENTS = [
    ("카우퍼", "cowper_weekly_report"),
    ("마실", "masil_weekly_report"),
    ("건테리어", "gunterior_weekly_report"),
    ("건테리어스", "gunteriors_weekly_report"),
    ("건테리어주택", "gunterior_house_weekly_report"),
    ("메카", "mecca_weekly_report"),
    ("다원세무회계", "dawon_weekly_report"),
    ("서휘건설", "seohwi_weekly_report"),
    ("신공간디자인", "shingonggan_weekly_report"),
    ("레솔", "leso_weekly_report"),
    ("꼼꼼", "kkomkkom_weekly_report"),
]

today = datetime.date.today()
title = f"주간 윤팀장 보고서 · {today.isoformat()}"
report_dir = Path(__file__).resolve().parent.parent / "reports"
pdfs = list(report_dir.glob("*.pdf"))
def find_pdf(pattern):
    for p in pdfs:
        if pattern in p.name: return p
    return None

# 1) DB 확보 (data_source_id 반환)
data_source_id = find_or_create_database()

# 2) 각 회사 PDF 업로드 + 파일 블록 만들기
children = [
    paragraph(f"자동 생성: {today.isoformat()}"),
    heading("📄 회사별 윤팀장 보고서", 2),
]

for name, prefix in CLIENTS:
    pdf = find_pdf(prefix)
    if not pdf:
        print(f"  ⚠ {name} PDF 없음")
        continue
    try:
        upload_id = upload_file(pdf)
        children.append(file_block(upload_id, f"{name} · {today.isoformat()}"))
        print(f"  ✅ {name} 업로드 ({pdf.stat().st_size // 1024} KB)")
    except Exception as ex:
        print(f"  ❌ {name} 실패: {ex}")

# 3) 실제 스키마 조회 → title/date/status 프로퍼티 이름 자동 감지 (select/status 둘 다 지원)
title_key, date_key, status_info = get_data_source_schema(data_source_id)
print(f"  📋 스키마: title={title_key!r}, date={date_key!r}, status={status_info!r}")

page_props = {}
if title_key:
    page_props[title_key] = {"title": rt(title)}
if date_key:
    page_props[date_key] = {"date": {"start": today.isoformat()}}
if status_info:
    sk, stype, sname = status_info
    page_props[sk] = {stype: {"name": sname}}

# 4) DB에 페이지 생성
resp = notion("pages", {
    "parent": {"type": "data_source_id", "data_source_id": data_source_id},
    "properties": page_props,
    "children": children,
})
print(f"\n✅ 노션 페이지 생성: {resp.get('url')}")
