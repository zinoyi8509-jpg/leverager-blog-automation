#!/usr/bin/env python3
"""매주 월요일 11개 회사 윤팀장 PDF 생성 → reports/ 폴더 (영문 파일명)."""
import os, sys, subprocess, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# 회사ID → 영문 파일명 접두어
NAME_MAP = {
    "cowper":         "cowper",
    "masil":          "masil",
    "mecca":          "mecca",
    "dawon":          "dawon",
    "seohwi":         "seohwi",
    "shingonggan":    "shingonggan",
    "gunterior":      "gunterior",
    "gunteriors":     "gunteriors",
    "gunterior_house":"gunterior_house",
    "leso":           "leso",
    "kkomkkom":       "kkomkkom",
}

CLIENTS = list(NAME_MAP.keys())

# 한글 접두어 → 영문 접두어 (파일명 복사 시 rename)
KO_TO_EN = {
    "카우퍼":       "cowper",
    "마실":         "masil",
    "메카":         "mecca",
    "다원세무회계": "dawon",
    "서휘건설":     "seohwi",
    "신공간디자인": "shingonggan",
    "건테리어":     "gunterior",
    "건테리어스":   "gunteriors",
    "건테리어주택": "gunterior_house",
    "레솔":         "leso",
    "꼼꼼":         "kkomkkom",
    "꼼꼼종합클린": "kkomkkom",
}

for client in CLIENTS:
    print(f"▶ {client}")
    try:
        r = subprocess.run(
            ["python3", "scripts/internal_report.py", client],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            print(f"  ⚠ 실패:\n  stdout: {r.stdout[-300:]}\n  stderr: {r.stderr[-500:]}")
            continue
        # PDF를 reports/ 로 복사 (한글 → 영문 rename)
        # 긴 접두어부터 매칭 (꼼꼼종합클린 → 꼼꼼 순으로 먼저 시도)
        for pdf in ROOT.glob("**/reports/internal/*_윤팀장_운영보고서_*.pdf"):
            new_name = pdf.name
            for ko, en in sorted(KO_TO_EN.items(), key=lambda x: -len(x[0])):
                new_name = new_name.replace(f"{ko}_윤팀장_운영보고서_", f"{en}_weekly_report_")
            shutil.copy(pdf, REPORTS / new_name)
            print(f"  ✅ {new_name}")
    except Exception as ex:
        print(f"  ⚠ 에러: {ex}")

pdf_count = len(list(REPORTS.glob('*.pdf')))
print(f"\n총 {pdf_count}개 PDF 생성")
