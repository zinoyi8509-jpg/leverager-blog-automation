#!/usr/bin/env python3
"""노션에 주간 윤팀장 보고서 페이지 생성 + PDF 파일 직접 첨부.
유림 페이지(Claude Automation 접근 가능) 아래에 "주간 윤팀장 보고서 YYYY-MM-DD" 페이지 생성.
"""
import os, sys, json, datetime, mimetypes
import urllib.request
from pathlib import Path

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "28c61e2336fd805b9a4bdf45a9b52a9f"

if not TOKEN:
    print("❌ NOTION_TOKEN 필요"); sys.exit(1)

NOTION_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
}

def notion(path, body):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(body).encode(),
        headers={**NOTION_HEADERS, "Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())

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
    # 1) 초기화
    init = notion("file_uploads", {
        "filename": pdf_path.name,
        "content_type": "application/pdf",
    })
    upload_id = init["id"]

    # 2) 파일 데이터 전송 (multipart/form-data)
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

# 각 회사 PDF 업로드 + 파일 블록 만들기
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

# 노션 페이지 생성
resp = notion("pages", {
    "parent": {"type": "page_id", "page_id": PARENT},
    "properties": {"title": {"title": rt(title)}},
    "children": children,
})
print(f"\n✅ 노션 페이지 생성: {resp.get('url')}")
