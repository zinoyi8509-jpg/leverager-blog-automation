#!/usr/bin/env python3
"""GitHub Release 링크를 포함한 노션 페이지 생성.
유림 페이지(Claude Automation 접근 가능) 아래에 "주간 윤팀장 보고서 YYYY-MM-DD" 페이지 생성.
"""
import os, sys, json, datetime
import urllib.request
from pathlib import Path

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
# 유림 페이지 ID (Claude Automation 초대 완료된 페이지)
PARENT = "28c61e2336fd805b9a4bdf45a9b52a9f"
REPO = os.environ.get("REPO", "zinoyi8509-jpg/leverager-blog-automation")
RUN_NUM = os.environ.get("RUN_NUM", "1")

if not TOKEN:
    print("❌ NOTION_TOKEN 필요"); sys.exit(1)

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
    return [{"type": "text", "text": {"content": text}, "annotations": {"bold": bold}}]

def link_block(name, url):
    return {"object": "block", "type": "bookmark", "bookmark": {"url": url, "caption": rt(name)}}

def paragraph(text, bold=False):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(text, bold)}}

def heading(text, level=2):
    return {"object": "block", "type": f"heading_{level}", f"heading_{level}": {"rich_text": rt(text)}}

today = datetime.date.today()
title = f"주간 윤팀장 보고서 · {today.isoformat()}"

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

report_dir = Path(__file__).resolve().parent.parent / "reports"
pdfs = list(report_dir.glob("*.pdf"))
def find_pdf(pattern):
    for p in pdfs:
        if pattern in p.name: return p.name
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
