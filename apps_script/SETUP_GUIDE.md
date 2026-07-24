# Notion ↔ Google Calendar 양방향 동기화 세팅 가이드

## 예상 소요: 15~20분

---

## STEP 1 — Notion Integration 만들기 (3분)

1. https://www.notion.so/my-integrations 접속
2. **"+ New integration"** 클릭
3. 정보 입력:
   - Name: `Calendar Sync`
   - Workspace: **"동오 최의 Notion"** (또는 대상 캘린더가 있는 워크스페이스)
   - Type: **Internal**
4. **Save**
5. 다음 화면에서 **"Internal Integration Secret"** 복사
   - `secret_xxxxxxxx...` 형태
   - ⚠ 이 secret은 저에게 공유하지 마세요! 오직 Apps Script에만 붙여넣기

---

## STEP 2 — 대상 노션 DB에 Integration 초대 (1분)

1. 대상 캘린더 DB 페이지 열기 (예: "새 데이터베이스")
2. 우측 상단 `⋯` → **"연결"** 선택
3. **"Calendar Sync"** 검색 → 클릭 → **페이지에 추가**

---

## STEP 3 — 노션 DB에 필요한 속성 추가 (3분)

DB에 아래 4개 속성이 있어야 합니다. 없으면 추가:

| 속성 이름 | 타입 | 용도 |
|---|---|---|
| **이름** | title | 이벤트 제목 (이미 있음) |
| **날짜** | date | 이벤트 날짜/시간 (이미 있으면 그대로) |
| **GCal Event ID** | text | 스크립트가 자동 관리 (직접 편집 X) |
| **마지막 동기화** | date (시간 포함) | 스크립트가 자동 관리 |

**속성 추가 방법**:
1. DB 우측 상단 `⋯` → **속성**
2. **+ 새 속성** → 이름·타입 선택

⚠ 속성 이름을 다르게 하려면 `notion_gcal_sync.gs` 상단 `FIELD_*` 상수도 함께 수정

---

## STEP 4 — Google Calendar ID 확보 (1분)

### 기본 캘린더 사용 시
`primary` 그대로 사용 (`zinoyi8509@gmail.com`)

### 별도 캘린더 사용 시
1. https://calendar.google.com 접속
2. 좌측 사이드바 → 대상 캘린더 옆 `⋯` → **설정 및 공유**
3. 페이지 아래 **"캘린더 통합"** → **"캘린더 ID"** 복사
   - 형태: `xxxxxxxx@group.calendar.google.com`

---

## STEP 5 — Google Apps Script 프로젝트 생성 (3분)

1. https://script.google.com 접속
2. **"새 프로젝트"** 클릭
3. 프로젝트 이름: `Notion Calendar Sync`
4. 왼쪽 `Code.gs` 파일을 열고 기존 내용 **모두 삭제**
5. `notion_gcal_sync.gs` 파일 내용을 **전체 복사 → 붙여넣기**
6. 상단 상수 3개 수정:
   ```javascript
   const NOTION_TOKEN = 'secret_xxxxxxxx';  // STEP 1의 secret
   const NOTION_DATABASE_ID = '3a761e2336fd80fb9f9ef20b1eddfa1f';  // 대상 DB ID (URL의 /p/ 뒤)
   const GCAL_ID = 'primary';  // 또는 xxx@group.calendar.google.com
   ```
7. **저장** (`Cmd + S`)

---

## STEP 6 — 첫 실행 + OAuth 승인 (2분)

1. 상단 함수 선택 드롭다운에서 **`syncAll`** 선택
2. **▶ 실행** 클릭
3. **"권한 검토"** → Google 계정 선택 → **"고급"** → **"안전하지 않음 (계속)"** → **"허용"**
   - 처음 실행이라 OAuth 승인 필요
   - Notion API + Google Calendar 접근 권한
4. 실행 완료 후 하단 **실행 로그** 확인
   - `✅ 완료` 나오면 성공

---

## STEP 7 — 5분마다 자동 실행 트리거 설정 (2분)

1. 함수 선택 드롭다운에서 **`setupTrigger`** 선택
2. **▶ 실행** 클릭
3. 실행 로그에 `✅ 트리거 설정 완료` 확인
4. 왼쪽 사이드바 **⏰ 트리거** 아이콘 클릭
5. `syncAll` 함수가 **5분마다** 실행되도록 등록된 것 확인

---

## STEP 8 — 테스트 (2분)

### 노션 → 구글 확인
1. 노션 DB에 새 카드 추가 (예: 제목 "테스트", 오늘 날짜)
2. 5분 대기 (또는 Apps Script에서 `syncAll` 수동 실행)
3. Google Calendar에서 "테스트" 이벤트 생성됐는지 확인

### 구글 → 노션 확인
1. Google Calendar에 새 이벤트 추가 (예: 제목 "테스트2", 내일 날짜)
2. 5분 대기 (또는 수동 실행)
3. 노션 DB에 "테스트2" 카드 생성됐는지 확인

---

## 🚨 문제 발생 시

### 실행 로그에서 오류 확인
Apps Script 왼쪽 사이드바 **"실행"** 아이콘 → 최근 실행 로그 확인

### 흔한 오류
| 오류 | 원인 | 해결 |
|---|---|---|
| `Notion API 401` | Token 잘못됨 | STEP 1 secret 다시 확인 |
| `Notion API 404` | DB에 Integration 안 초대됨 | STEP 2 다시 |
| `data_source 없음` | DB ID 오류 | STEP 5 DB ID 확인 |
| `properties.X is not a property` | 필드명 불일치 | STEP 3 필드 이름 또는 스크립트 `FIELD_*` 수정 |
| `Calendar not found` | GCal ID 오류 | STEP 4 다시 |

---

## ⚠ 알아야 할 것

### 삭제 처리
- 이 스크립트는 **삭제 sync를 하지 않습니다**
- 노션에서 카드 삭제해도 구글 이벤트는 남음 (반대도 마찬가지)
- 삭제 sync를 원하면 별도 로직 추가 필요 (사용자 요청 시 안내)

### 충돌 처리
- 노션과 구글 양쪽 모두 5분 안에 수정하면 → 나중에 sync된 쪽이 우선
- 정확한 conflict resolution 원하면 별도 로직 필요

### 조회 범위
- 앞 3개월 ~ 뒤 12개월 이벤트만 처리
- 필요시 `fetchGCalEvents` 함수 수정

### 실행 로그
- Apps Script 실행 로그 최근 실행분만 저장
- 오래된 실행 결과는 자동 삭제됨

---

## 완료 후 저에게 알려주세요
- 잘 되면: "완료" 라고 해주세요
- 안 되면: 오류 메시지 or 스크린샷 공유 → 함께 디버깅
