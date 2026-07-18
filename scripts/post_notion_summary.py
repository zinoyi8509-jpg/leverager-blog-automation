#!/usr/bin/env python3
"""GitHub Release 링크를 포함한 노션 페이지 생성.
NOTION_PARENT_PAGE_ID 아래에 "주간 윤팀장 보고서 YYYY-MM-DD" 페이지 생성.
"""
import os, sys, json, datetime
import urllib.request
from pathlib import Path

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = (os.environ.get("NOTION_PARENT_PAGE_ID") or "").strip()
REPO = os.environ.get("REPO", "zinoyi8509-jpg/leverager-blog-automation")
RUN_NUM = os.environ.get("RUN_NUM", "1")

if not TOKEN or not PARENT:
    print("❌ NOTION_TOKEN, NOTION_PARENT_PAGE_ID 필요"); sys.exit(1)

def notion(path, body):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    return json.loads(urllib.request.urlopen(req).read())

def rt(text, bold=False):
    """rich text 헬퍼"""
    return [{"type": "text", "text": {"content": text}, "annotations": {"bold": bold}}]

def link_block(name, url):
    return {
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": url, "caption": rt(name)},
    }

def paragraph(text, bold=False):
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": rt(text, bold)}}

def heading(text, level=2):
    return {"object": "block", "type": f"heading_{level}",
            f"heading_{level}": {"rich_text": rt(text)}}

today = datetime.date.today()
title = f"주간 윤팀장 보고서 · {today.isoformat()}"

# 11개 회사별 PDF 링크 (Release asset)
CLIENTS = [
    ("카우퍼", "카우퍼_윤팀장_운영보고서"),
    ("마실", "마실_윤팀장_운영보고서"),
    ("건테리어", "건테리어_윤팀장_운영보고서"),
    ("건테리어스", "건테리어스_윤팀장_운영보고서"),
    ("건테리어주택", "건테리어주택_윤팀장_운영보고서"),
    ("메카", "메카_윤팀장_운영보고서"),
    ("다원세무회계", "다원세무회계_윤팀장_운영보고서"),
    ("서휘건설", "서휘건설_윤팀장_운영보고서"),
    ("신공간디자인", "신공간디자인_윤팀장_운영보고서"),
    ("레솔", "레솔_윤팀장_운영보고서"),
    ("꼼꼼", "꼼꼼_윤팀장_운영보고서"),
]

# 리포트 폴더에서 실제 파일명 찾기
report_dir = Path(__file__).resolve().parent.parent / "reports"
pdfs = list(report_dir.glob("*.pdf"))
def find_pdf(pattern):
    for p in pdfs:
        if pattern in p.name:
            return p.name
    return None

release_base = f"https://github.com/{REPO}/releases/download/weekly-{RUN_NUM}"

children = [
    paragraph(f"자동 생성: {today.isoformat()} · GitHub Actions 실행 #{RUN_NUM}"),
    heading("📄 회사별 보고서 다운로드", 2),
]

for name, prefix in CLIENTS:
    fname = find_pdf(prefix)
    if fname:
        url_safe = fname.replace(" ", ".").replace("(", "%28").replace(")", "%29")
        children.append(link_block(f"{name} 윤팀장 보고서 · {today.isoformat()}",
                                    f"{release_base}/{url_safe}"))

resp = notion("pages", {
    "parent": {"type": "page_id", "page_id": PARENT},
    "properties": {"title": {"title": rt(title)}},
    "children": children,
})
print(f"✅ 노션 페이지 생성: {resp.get('url')}")
