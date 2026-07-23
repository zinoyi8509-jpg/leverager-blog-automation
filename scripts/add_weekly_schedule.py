#!/usr/bin/env python3
"""주간 보고서 페이지 안에 '📅 주간 일정표' 토글 + 표 삽입 (원샷).
매주 발행 스케줄을 시각화. 이미 존재하면 중복 삽입 방지.
"""
import os, sys, json
import urllib.request, urllib.error

TOKEN = (os.environ.get("NOTION_TOKEN") or "").strip()
PARENT = "3a661e2336fd8041abdac15972e10e14"  # 주간 보고서 페이지

if not TOKEN:
    print("❌ NOTION_TOKEN 필요"); sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}

def api(path, body=None, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data, headers=HEADERS, method=method,
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"❌ {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")
        raise


def rt(text, bold=False):
    return [{"type": "text", "text": {"content": text},
             "annotations": {"bold": bold} if bold else {}}]


def cell(text, bold=False):
    if not text:
        return []
    return rt(text, bold)


def row(cells, bold_first=False):
    return {
        "object": "block",
        "type": "table_row",
        "table_row": {
            "cells": [cell(c, bold=(bold_first and i == 0))
                      for i, c in enumerate(cells)]
        },
    }


# 발행 스케줄 데이터 (요일별: 월/화/수/목/금)
# 표기: "회사명+개수" 또는 빈문자열
NAVER_ROWS = [
    ("다원",       ["다원1", "",       "다원1", "",       "다원1"]),
    ("마실",       ["마실2", "마실2",  "마실2", "마실2",  "마실2"]),
    ("카우퍼",     ["카우퍼1", "카우퍼1", "카우퍼1", "카우퍼1", "카우퍼1"]),
    ("신공간",     ["신공간1", "신공간1", "신공간1", "신공간1", "신공간1"]),
    ("서휘",       ["서휘1", "",       "서휘1", "",       "서휘1"]),
    ("꼼꼼",       ["꼼꼼1", "",       "꼼꼼1", "",       "꼼꼼1"]),
    ("건축사",     ["건축사1", "건축사1", "건축사1", "건축사1", "건축사1"]),
    ("건테리어스", ["",     "건테리어스1", "",     "건테리어스1", ""]),
    ("주택건축",   ["",     "주택건축1",   "",     "주택건축1",   ""]),
    ("건테리어",   ["건테리어2", "건테리어2", "건테리어2", "건테리어2", "건테리어2"]),
]

TISTORY_ROWS = [
    ("마실",       ["",       "마실1",   "",       "마실1",   "마실1"]),
    ("건테리어",   ["건테리어1", "",     "건테리어1", "건테리어1", ""]),
]

TOTAL_ROW = ["11개", "10개", "11개", "11개", "11개"]

# 표 자식 rows 조립
table_children = [
    row(["월", "화", "수", "목", "금"]),                            # 헤더
    row(["네이버 블로그", "", "", "", ""], bold_first=True),         # 섹션
]
for _, cells in NAVER_ROWS:
    table_children.append(row(cells))
table_children.append(row(["티스토리", "", "", "", ""], bold_first=True))
for _, cells in TISTORY_ROWS:
    table_children.append(row(cells))
table_children.append(row(TOTAL_ROW, bold_first=False))  # 총합

# Toggle 블록
toggle_block = {
    "object": "block",
    "type": "toggle",
    "toggle": {
        "rich_text": rt("📅 주간 일정표", bold=True),
        "children": [
            {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 5,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": [{**tr} for tr in table_children],
                },
            }
        ],
    },
}


# 중복 방지: 페이지 자식들 중 "📅 주간 일정표" 토글이 이미 있는지 확인
def has_existing_toggle():
    cursor = None
    while True:
        path = f"blocks/{PARENT}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        req = urllib.request.Request(
            f"https://api.notion.com/v1/{path}",
            headers=HEADERS, method="GET",
        )
        resp = json.loads(urllib.request.urlopen(req).read())
        for b in resp.get("results", []):
            if b.get("type") == "toggle":
                rich = (b.get("toggle") or {}).get("rich_text") or []
                text = "".join(x.get("plain_text", "") for x in rich)
                if "주간 일정표" in text:
                    print(f"  ⚠ 이미 존재: {b['id']}")
                    return True
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return False


if has_existing_toggle():
    print("이미 '📅 주간 일정표' 토글이 있어서 스킵")
    sys.exit(0)

# 페이지에 토글 append
resp = api(f"blocks/{PARENT}/children", {"children": [toggle_block]}, method="PATCH")
print(f"✅ '📅 주간 일정표' 토글 삽입 완료")
print(f"   블록 ID: {resp['results'][0]['id']}")
