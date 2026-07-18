#!/usr/bin/env python3
"""
매일 노션 유림 캘린더에서 어제 데이터를 가져와 history.json에 적재.

노션 API 사용. 인테그레이션 "Claude Automation" 토큰 필요 (NOTION_TOKEN 환경 변수).

캘린더 페이지 ID: 28c61e2336fd811eb1f1f00ff5e29654 (유림 캘린더 DB)
"""
import os, sys, json, datetime, re
from pathlib import Path
import urllib.request

TOKEN = os.environ.get("NOTION_TOKEN")
if not TOKEN:
    print("❌ NOTION_TOKEN 환경 변수 필요")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history.json"

# 유림 대시보드 부모 페이지 ID (search로 찾아야 함)
# 실제 캘린더 페이지들은 search로 발견

def notion_get(path):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": "2022-06-28",
        },
    )
    return json.loads(urllib.request.urlopen(req).read())

def notion_post(path, body):
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

def find_yurim_pages():
    """어제 날짜 페이지 검색"""
    yesterday = (datetime.date.today() - datetime.timedelta(days=1))
    mmdd = yesterday.strftime("%m%d")
    result = notion_post("search", {
        "query": mmdd,
        "filter": {"value": "page", "property": "object"},
        "page_size": 5,
    })
    return result.get("results", [])

def extract_text(block):
    """블록에서 텍스트 추출"""
    t = block.get("type")
    if not t: return ""
    content = block.get(t, {})
    rich = content.get("rich_text", [])
    return "".join(r.get("plain_text", "") for r in rich)

def get_page_content(page_id):
    """페이지의 모든 텍스트 블록 순회"""
    result = notion_get(f"blocks/{page_id}/children?page_size=100")
    lines = []
    for block in result.get("results", []):
        text = extract_text(block)
        if text.strip():
            lines.append(text.strip())
    return "\n".join(lines)

def parse_yurim_text(text):
    """유림 표준 텍스트 파싱"""
    # [키워드] 섹션 추출
    m = re.search(r"\[키워드\]\s*(.+?)(?=\[|$)", text, re.DOTALL)
    if not m: return {}
    kw_block = m.group(1).strip()
    # 각 줄 (회사) 파싱
    company_map = {
        "마실": "chanwoo0919",
        "마실-T": "masil0919_t",
        "카우퍼": "cowper7710",
        "다원": "kbtax0503",
        "건테리어": "cdo2795",
        "건테리어-T": "cdo2795_t",
        "건테리어스": "cdo27952",
        "건테리어주택": "cdo27951",
        "주택건축": "cdo27951",  # 별칭
        "메카": "cdo27953",
        "건축사": "cdo27953",  # 별칭
        "레솔": "leverager_solution",
        "레솔-T": "leverager_solution_t",
        "서휘": "sh33391",
        "신공간": "shingonggandesign02",
    }
    result = {}
    for line in kw_block.split("\n"):
        line = line.strip()
        if not line: continue
        # "1. 키워드1, 키워드2 (회사)" 형태
        m = re.match(r"(?:\d+\.\s*)?(.+?)\s*\(([^)]+)\)$", line)
        if not m: continue
        kws_str, comp = m.group(1), m.group(2).strip()
        kws = [k.strip() for k in kws_str.split(",") if k.strip()]
        if comp in company_map:
            bid = company_map[comp]
            result.setdefault(bid, []).extend(kws)
    return result

def main():
    print("📡 노션 유림 페이지 검색 중...")
    pages = find_yurim_pages()
    if not pages:
        print("❌ 어제 날짜 페이지 없음")
        return

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    date_str = yesterday.isoformat()
    ym = date_str[:7]

    # 첫 번째 매칭 페이지 사용
    page = pages[0]
    print(f"📄 페이지: {page['id']}")

    content = get_page_content(page["id"])
    if "비어" in content:
        print("⚠ 페이지 비어있음")
        return

    print(f"📝 내용 발췌:\n{content[:500]}")

    parsed = parse_yurim_text(content)
    if not parsed:
        print("⚠ 키워드 파싱 결과 없음")
        return

    print(f"\n✅ 파싱 결과 (회사 {len(parsed)}개):")
    for bid, kws in parsed.items():
        print(f"  {bid}: {kws}")

    # history.json 적재
    if not HIST.exists():
        print(f"⚠ {HIST} 없음 — 새로 생성")
        HIST.parent.mkdir(exist_ok=True)
        json.dump({"blogs": {}, "tistory": {}}, open(HIST, "w"), ensure_ascii=False, indent=2)

    h = json.load(open(HIST, encoding="utf-8"))
    for bid, kws in parsed.items():
        # 티스토리 여부
        if bid.endswith("_t"):
            tid = bid[:-2]
            if tid not in h.get("tistory", {}):
                h.setdefault("tistory", {})[tid] = {}
            target = h["tistory"][tid]
        else:
            if bid not in h.get("blogs", {}):
                h.setdefault("blogs", {})[bid] = {}
            target = h["blogs"][bid]

        sub_month = target.setdefault("keywords", {}).setdefault("sub", {}).setdefault(ym, {})
        by_date = sub_month.setdefault("by_date", {})
        by_date[date_str] = kws
        uk = sub_month.setdefault("unique_keywords", [])
        for k in kws:
            if k not in uk: uk.append(k)

    json.dump(h, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✅ history.json 갱신 완료 ({date_str})")

if __name__ == "__main__":
    main()
