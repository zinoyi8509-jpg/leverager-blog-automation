# leverager-blog-automation

Leverager blog automation pipeline (daily 7pm auto-run)

## 매일 자동 실행 흐름

**KST 저녁 7시** (`0 10 * * *` UTC) 자동 실행:

1. **노션 유림 캘린더 파싱** — 어제 날짜 페이지에서 서브 키워드 자동 추출
2. **Playwright 순위 측정** — Naver 블로그탭 실측 순위 확인
3. **결과 보고서 생성** — 각 회사 요약 로그 출력
4. **history.json 커밋** — 갱신된 데이터 자동 push

## 수동 실행

Actions 탭 → `Daily Blog Automation` → `Run workflow`

## Secrets

- `NOTION_TOKEN`: 노션 인테그레이션 "Claude Automation" 액세스 토큰
