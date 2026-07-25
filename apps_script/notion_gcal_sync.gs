/**
 * Notion ↔ Google Calendar 양방향 동기화
 * 5분마다 자동 실행
 *
 * 세팅:
 * 1. 상수 3개 입력 (NOTION_TOKEN, NOTION_DATABASE_ID, GCAL_ID)
 * 2. 노션 DB에 다음 속성 추가:
 *    - 제목 (title)      ← 기본
 *    - 날짜 (date)       ← 반드시 있어야 함
 *    - GCal Event ID (text) ← 연결 추적용
 *    - 마지막 동기화 (date, "date & time" 켜기) ← sync 시각
 * 3. Notion Integration을 대상 DB에 초대 (필수)
 */

// ==================== 설정 ====================
const NOTION_TOKEN = 'secret_YOUR_NOTION_INTEGRATION_TOKEN_HERE';  // ← Calendar Sync Integration Secret 붙여넣기
const NOTION_DATABASE_ID = '3a761e2336fd80fb9f9ef20b1eddfa1f';    // 대상 DB ID (새 데이터베이스) ✅ 세팅됨
const GCAL_ID = 'zinoyi8509@gmail.com';  // 이진호 캘린더 ✅ 세팅됨

// 필드명 (사용자 DB에 맞춰 세팅됨)
const FIELD_TITLE = '이름';        // ✅ 있음
const FIELD_DATE = '날짜';         // ✅ 있음
const FIELD_GCAL_ID = 'GCal Event ID';  // ✅ 자동 추가됨
const FIELD_SYNCED = '마지막 동기화';    // ✅ 자동 추가됨

const NOTION_VERSION = '2025-09-03';

// ==================== 메인 ====================
function syncAll() {
  Logger.log('=== Notion ↔ Google Calendar Sync 시작 ===');
  try {
    const notionPages = fetchNotionPages();
    const gcalEvents = fetchGCalEvents();
    Logger.log(`노션 페이지 ${notionPages.length}개, GCal 이벤트 ${gcalEvents.length}개`);

    syncNotionToGCal(notionPages, gcalEvents);
    syncGCalToNotion(gcalEvents, notionPages);

    Logger.log('✅ 완료');
  } catch (e) {
    Logger.log('❌ 오류: ' + e.message);
    throw e;
  }
}

// ==================== Notion → GCal ====================
function syncNotionToGCal(notionPages, gcalEvents) {
  const gcalById = {};
  gcalEvents.forEach(ev => { gcalById[ev.getId()] = ev; });
  const calendar = CalendarApp.getCalendarById(GCAL_ID === 'primary' ? Session.getActiveUser().getEmail() : GCAL_ID);

  for (const page of notionPages) {
    const props = page.properties;
    const title = readTitle(props[FIELD_TITLE]);
    const date = readDate(props[FIELD_DATE]);
    const gcalIdProp = readText(props[FIELD_GCAL_ID]);
    const lastSynced = readDate(props[FIELD_SYNCED]);
    const pageLastEdited = new Date(page.last_edited_time);

    if (!title || !date) continue;  // 필수 정보 없으면 skip

    // 이미 sync됐고 노션에 변경 없으면 skip
    if (gcalIdProp && lastSynced && pageLastEdited <= lastSynced) continue;

    try {
      let event;
      if (gcalIdProp && gcalById[gcalIdProp]) {
        // 기존 이벤트 업데이트
        event = gcalById[gcalIdProp];
        // 반복 이벤트는 수정하지 않음 (안전)
        if (event.isRecurringEvent && event.isRecurringEvent()) {
          Logger.log(`  ⏭ 반복 이벤트 skip: ${title}`);
          continue;
        }
        event.setTitle(title);
        if (date.start && date.end) {
          event.setTime(date.start, date.end);
        } else if (date.start) {
          event.setAllDayDate(date.start);
        }
        Logger.log(`  ✏ Notion→GCal 수정: ${title}`);
      } else if (gcalIdProp) {
        // gcal id 있는데 매칭 실패 → 안전을 위해 skip (복제 방지)
        Logger.log(`  ⚠ ID 매칭 실패 skip: ${title} (gcal_id=${gcalIdProp.substring(0, 20)}...)`);
        continue;
      } else {
        // 새 이벤트 생성 (노션에서 새로 만든 카드만)
        if (date.start && date.end) {
          event = calendar.createEvent(title, date.start, date.end);
        } else {
          event = calendar.createAllDayEvent(title, date.start);
        }
        Logger.log(`  ➕ Notion→GCal 생성: ${title}`);
      }
      // 노션 페이지 업데이트 (gcal id + last synced)
      updateNotionPage(page.id, {
        [FIELD_GCAL_ID]: { rich_text: [{ text: { content: event.getId() } }] },
        [FIELD_SYNCED]: { date: { start: new Date().toISOString() } },
      });
    } catch (e) {
      Logger.log(`  ❌ ${title} 실패: ${e.message}`);
    }
  }
}

// ==================== GCal → Notion ====================
function syncGCalToNotion(gcalEvents, notionPages) {
  const notionByGcalId = {};
  notionPages.forEach(p => {
    const gid = readText(p.properties[FIELD_GCAL_ID]);
    if (gid) notionByGcalId[gid] = p;
  });

  for (const ev of gcalEvents) {
    // 반복 이벤트는 sync 대상에서 제외 (ID 매칭 이슈로 복제 위험)
    if (ev.isRecurringEvent && ev.isRecurringEvent()) continue;

    const gid = ev.getId();
    const title = ev.getTitle();
    const start = ev.getStartTime();
    const end = ev.getEndTime();
    const isAllDay = ev.isAllDayEvent();
    const evLastUpdated = ev.getLastUpdated();

    if (!title) continue;

    const existing = notionByGcalId[gid];
    if (existing) {
      // 기존 노션 페이지 업데이트 (GCal이 더 최신이면)
      const lastSynced = readDate(existing.properties[FIELD_SYNCED]);
      if (lastSynced && evLastUpdated <= lastSynced.start) continue;

      try {
        updateNotionPage(existing.id, {
          [FIELD_TITLE]: { title: [{ text: { content: title } }] },
          [FIELD_DATE]: { date: isAllDay
            ? { start: formatDate(start) }
            : { start: start.toISOString(), end: end.toISOString() } },
          [FIELD_SYNCED]: { date: { start: new Date().toISOString() } },
        });
        Logger.log(`  ✏ GCal→Notion 수정: ${title}`);
      } catch (e) {
        Logger.log(`  ❌ ${title} 수정 실패: ${e.message}`);
      }
    } else {
      // 새 노션 페이지 생성
      try {
        createNotionPage({
          [FIELD_TITLE]: { title: [{ text: { content: title } }] },
          [FIELD_DATE]: { date: isAllDay
            ? { start: formatDate(start) }
            : { start: start.toISOString(), end: end.toISOString() } },
          [FIELD_GCAL_ID]: { rich_text: [{ text: { content: gid } }] },
          [FIELD_SYNCED]: { date: { start: new Date().toISOString() } },
        });
        Logger.log(`  ➕ GCal→Notion 생성: ${title}`);
      } catch (e) {
        Logger.log(`  ❌ ${title} 생성 실패: ${e.message}`);
      }
    }
  }
}

// ==================== Notion API ====================
function notionRequest(path, method, payload) {
  const url = `https://api.notion.com/v1/${path}`;
  const options = {
    method: method,
    headers: {
      Authorization: `Bearer ${NOTION_TOKEN}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    muteHttpExceptions: true,
  };
  if (payload) options.payload = JSON.stringify(payload);
  const resp = UrlFetchApp.fetch(url, options);
  const code = resp.getResponseCode();
  if (code >= 400) {
    Logger.log(`❌ Notion API ${code}: ${resp.getContentText().substring(0, 400)}`);
    throw new Error(`Notion API ${code}`);
  }
  return JSON.parse(resp.getContentText());
}

function getDataSourceId() {
  const db = notionRequest(`databases/${NOTION_DATABASE_ID}`, 'GET');
  const sources = db.data_sources || [];
  if (!sources.length) throw new Error('data_source 없음');
  return sources[0].id;
}

function fetchNotionPages() {
  const dsId = getDataSourceId();
  const pages = [];
  let cursor = null;
  do {
    const body = { page_size: 100 };
    if (cursor) body.start_cursor = cursor;
    const resp = notionRequest(`data_sources/${dsId}/query`, 'POST', body);
    pages.push(...(resp.results || []));
    cursor = resp.has_more ? resp.next_cursor : null;
  } while (cursor);
  return pages;
}

function createNotionPage(properties) {
  const dsId = getDataSourceId();
  return notionRequest('pages', 'POST', {
    parent: { type: 'data_source_id', data_source_id: dsId },
    properties: properties,
  });
}

function updateNotionPage(pageId, properties) {
  return notionRequest(`pages/${pageId}`, 'PATCH', { properties: properties });
}

// ==================== GCal ====================
function fetchGCalEvents() {
  const calendar = CalendarApp.getCalendarById(GCAL_ID === 'primary' ? Session.getActiveUser().getEmail() : GCAL_ID);
  // 앞 3개월 ~ 뒤 12개월
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth() - 3, 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 12, 31);
  return calendar.getEvents(from, to);
}

// ==================== 헬퍼 ====================
function readTitle(prop) {
  if (!prop || prop.type !== 'title') return null;
  return (prop.title || []).map(t => t.plain_text).join('');
}

function readDate(prop) {
  if (!prop || prop.type !== 'date' || !prop.date) return null;
  return {
    start: prop.date.start ? new Date(prop.date.start) : null,
    end: prop.date.end ? new Date(prop.date.end) : null,
  };
}

function readText(prop) {
  if (!prop) return null;
  if (prop.type === 'rich_text') return (prop.rich_text || []).map(t => t.plain_text).join('');
  return null;
}

function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// ==================== 트리거 세팅 (수동 1회 실행) ====================
function setupTrigger() {
  // 기존 트리거 제거
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'syncAll') ScriptApp.deleteTrigger(t);
  });
  // 5분마다
  ScriptApp.newTrigger('syncAll').timeBased().everyMinutes(5).create();
  Logger.log('✅ 트리거 설정 완료 (5분마다)');
}
