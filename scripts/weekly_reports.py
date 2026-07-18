#!/usr/bin/env python3
"""매주 월요일 11개 회사 윤팀장 PDF 생성 → reports/ 폴더."""
import os, sys, subprocess, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# 11개 회사 (internal_report.py 와 동일한 CLIENTS)
CLIENTS = [
    "cowper", "masil", "mecca", "dawon", "seohwi", "shingonggan",
    "gunterior", "gunteriors", "gunterior_house", "leso", "kkomkkom",
]

for client in CLIENTS:
    print(f"▶ {client}")
    try:
        r = subprocess.run(
            ["python3", "scripts/internal_report.py", client],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            print(f"  ⚠ 실패: {r.stderr[-500:]}")
            continue
        # PDF 는 internal_report 가 자체 경로에 저장. 찾아서 reports/ 로 복사
        for pdf in ROOT.glob("**/reports/internal/*_윤팀장_운영보고서_*.pdf"):
            shutil.copy(pdf, REPORTS / pdf.name)
            print(f"  ✅ {pdf.name}")
    except Exception as ex:
        print(f"  ⚠ 에러: {ex}")

print(f"\n총 {len(list(REPORTS.glob('*.pdf')))}개 PDF 생성")
