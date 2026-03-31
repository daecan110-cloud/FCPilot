/**
 * FCPilot 텔레그램 봇 v5 — 100% Gemini NLP, 10가지 action
 */
import { createClient } from "npm:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID")!;
const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// ── 세션 (DB 저장) ──────────────────────────────────

interface Session {
  last_customer_name: string;
  last_customer_id: string;
  pending_selection: Array<{ id: string; name: string; info: string }>;
  pending_action: string;
  pending_fields: Record<string, unknown>;
}

async function loadSession(chatId: string): Promise<Session> {
  const { data } = await supabase
    .from("bot_sessions").select("*").eq("chat_id", chatId).single();

  if (data) return {
    last_customer_name: data.last_customer_name || "",
    last_customer_id: data.last_customer_id || "",
    pending_selection: data.pending_selection || [],
    pending_action: data.pending_action || "",
    pending_fields: data.pending_fields || {},
  };
  return { last_customer_name: "", last_customer_id: "", pending_selection: [], pending_action: "", pending_fields: {} };
}

async function saveSession(chatId: string, s: Session) {
  await supabase.from("bot_sessions").upsert({
    chat_id: chatId,
    last_customer_name: s.last_customer_name,
    last_customer_id: s.last_customer_id,
    pending_selection: s.pending_selection,
    pending_action: s.pending_action,
    pending_fields: s.pending_fields,
    updated_at: new Date().toISOString(),
  });
}

// ── 텔레그램 ────────────────────────────────────────

async function reply(chatId: string, text: string) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "Markdown" }),
  });
}

// ── 나이 파싱 ───────────────────────────────────────

function parseAge(input: string) {
  const t = (input || "").trim();
  const yr = new Date().getFullYear();

  const birth = t.match(/(\d{2,4})\s*년생/);
  if (birth) {
    let y = parseInt(birth[1]);
    if (y < 100) y += y <= (yr % 100) ? 2000 : 1900;
    const a = yr - y;
    return { age_group: `${Math.floor(a / 10) * 10}대 (${a}세)`, age: a, birth_year: y };
  }

  const exact = t.match(/(\d{1,3})\s*(살|세)/);
  if (exact) {
    const a = parseInt(exact[1]);
    return { age_group: `${Math.floor(a / 10) * 10}대 (${a}세)`, age: a, birth_year: yr - a };
  }

  const decade = t.match(/(\d{1,2})0?\s*대/);
  if (decade) {
    const d = parseInt(decade[1]) * 10;
    return { age_group: `${d}대`, age: d, birth_year: null };
  }

  const num = t.match(/^(\d{1,3})$/);
  if (num) {
    const n = parseInt(num[1]);
    if (n >= 10 && n <= 99)
      return { age_group: `${Math.floor(n / 10) * 10}대 (${n}세)`, age: n, birth_year: yr - n };
  }

  return { age_group: t || null, age: null as number | null, birth_year: null as number | null };
}

// ── Gemini API ──────────────────────────────────────

const SYSTEM_PROMPT = `너는 보험 FC 업무 비서 봇이다. 사용자의 자연어 메시지를 분석해서 반드시 JSON만 응답해.

{
  "action": "query|register|update|delete|delete_all|reminder|contact|visit|command|search|stats",
  "name": "고객 이름 (없으면 null)",
  "fields": { "수정할 필드": "값" },
  "params": { "등록/검색 파라미터": "값" },
  "contact": { "touch_method": "방법", "memo": "내용", "next_date": "YYYY-MM-DD", "next_action": "다음 액션" },
  "visit": { "visit_datetime": "YYYY-MM-DDTHH:MM:00", "memo": "메모" },
  "command": "명령 텍스트",
  "message": "추가 메시지"
}

## action 규칙
- query: 고객 조회. "양종학", "양종학 정보", "수원 사는 고객"
- register: 등록. 키워드: 등록/추가/새고객/신규/넣어
  params: name, age, grade, address, memo, occupation, gender
- update: 수정. 키워드: 변경/수정/바꿔/으로/올려/내려
  fields: {"등급":"B","나이":"36살","주소":"서울"} — 이름 없으면 name=null(직전 고객)
- delete: 단건 삭제. 확인 없이 바로 삭제.
- delete_all: 동명이인 전체 삭제. "전체삭제/다 삭제/전부 지워"
- reminder: 리마인드/할일. "할일/오늘 뭐해/이번주 일정/미접촉 고객"
- contact: 상담 기록. "통화함/만남/문자/상담함"
  contact: {touch_method, memo, next_date(YYYY-MM-DD), next_action}
- visit: 방문 예약. "방문/예약/내일 3시"
  visit: {visit_datetime(ISO8601), memo}
- command: PC 명령. "테스트해줘/git push/handoff"
- search: 조건 검색. "A등급 고객 전체/수원 고객/이번달 등록"
  params: {grade, address, period("today"|"week"|"month"), keyword}
- stats: 통계. "고객 몇명/이번달 상담 몇건/등급별 현황"
  params: {type: "total"|"grade"|"contact"|"pioneer"}
- select: 번호 선택 (1~9 숫자만). action="select", params.number=숫자

## 자연어 매핑
- "빼줘/지워" = delete, "넣어줘" = register, "b로 올려" = update 등급 B
- "방금 거 삭제" = delete (name=null), "오늘 통화함 관심있다고 함" = contact
- "내일 3시 방문" = visit (오늘 기준 날짜 계산)

## 나이: 원문 그대로. "23세"→"23세", "00년생"→"00년생", "20대"→"20대"
## 전화번호: params/fields에 절대 포함하지 마.
## JSON만. 설명X. 코드블록X.`;

async function callGemini(text: string, session: Session): Promise<Record<string, unknown>> {
  const ctx = session.last_customer_name
    ? `현재 세션 고객: "${session.last_customer_name}"`
    : "현재 세션 고객: 없음";
  const hasPending = session.pending_selection.length > 0
    ? `동명이인 선택 대기 중 (${session.pending_selection.length}명)`
    : "";

  const userPrompt = `${ctx}\n${hasPending}\n\n메시지: "${text}"`;
  const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_KEY}`;
  const body = JSON.stringify({
    contents: [
      { role: "user", parts: [{ text: SYSTEM_PROMPT }] },
      { role: "model", parts: [{ text: '{"action":"query"}' }] },
      { role: "user", parts: [{ text: userPrompt }] },
    ],
    generationConfig: { temperature: 0, maxOutputTokens: 512 },
  });

  // 최대 2회 시도 (429 시 4초 대기)
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(apiUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body });

      if (res.status === 429) {
        if (attempt === 0) { await new Promise(r => setTimeout(r, 4000)); continue; }
        return { action: "rate_limited" };
      }

      const data = await res.json();
      const raw = (data?.candidates?.[0]?.content?.parts?.[0]?.text || "").trim();
      if (!raw) break;

      const cleaned = raw.replace(/```json\n?/g, "").replace(/```/g, "").trim();

      // JSON 파싱 실패 시 1회 재시도
      try {
        return JSON.parse(cleaned);
      } catch {
        if (attempt === 0) { await new Promise(r => setTimeout(r, 1000)); continue; }
        console.error("JSON parse fail:", cleaned.slice(0, 100));
      }
    } catch (e) {
      console.error("Gemini error:", e);
    }
  }

  return { action: "unknown" };
}

// ── 핸들러 ──────────────────────────────────────────

async function handleQuery(name: string, session: Session, fcId: string): Promise<string> {
  const query = supabase.from("clients")
    .select("id, name, prospect_grade, age, age_group, birth_year, gender, occupation, address, memo")
    .eq("fc_id", fcId);

  const { data, error } = name
    ? await query.ilike("name", `%${name}%`).limit(10)
    : await query.limit(5);

  if (error) return `❌ 조회 실패: ${error.message}`;
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  if (data.length === 1) {
    session.last_customer_name = data[0].name;
    session.last_customer_id = data[0].id;
  }

  return data.map((c, i) => {
    let ageStr = "";
    if (c.age_group) {
      ageStr = c.age_group;
      if (c.birth_year) {
        const sy = String(c.birth_year).slice(-2);
        if (!ageStr.includes("년생")) ageStr += ` (${sy}년생)`;
      }
    } else if (c.age) ageStr = `${c.age}세`;

    const genderStr = c.gender === "M" ? "남" : c.gender === "F" ? "여" : "";
    const info = [ageStr, genderStr, c.occupation, c.address].filter(Boolean).join(" / ");
    const memo = c.memo ? `\n  메모: ${c.memo}` : "";
    const num = data.length > 1 ? `${i + 1}. ` : "";
    return `${num}👤 *${c.name}* [${c.prospect_grade || "-"}등급]\n  ${info || "정보 없음"}${memo}`;
  }).join("\n\n");
}

async function handleRegister(params: Record<string, unknown>, fcId: string, session: Session): Promise<string> {
  const name = String(params.name || "").trim();
  if (!name) return "❌ 고객 이름이 필요합니다.";

  const grade = String(params.grade || params.prospect_grade || params["등급"] || "C").toUpperCase();
  const ins: Record<string, unknown> = {
    fc_id: fcId, name,
    address: params.address || params["주소"] || params["지역"] || "",
    memo: params.memo || params["메모"] || "",
    occupation: params.occupation || params["직업"] || "",
    prospect_grade: grade,
    gender: params.gender || params["성별"] || "",
  };

  const ageRaw = String(params.age || params["나이"] || "").trim();
  if (ageRaw) {
    const info = parseAge(ageRaw);
    if (info.age_group) ins.age_group = info.age_group;
    if (info.age !== null) ins.age = info.age;
    if (info.birth_year !== null) ins.birth_year = info.birth_year;
  }

  const { data, error } = await supabase.from("clients").insert(ins).select("id").single();
  if (error) return `❌ 등록 실패: ${error.message}`;

  session.last_customer_name = name;
  session.last_customer_id = data?.id || "";

  const lines = [`✅ *${name}* 등록 완료`, `  • 등급: ${grade}`];
  if (ins.age_group) lines.push(`  • 나이: ${ins.age_group}`);
  if (ins.address) lines.push(`  • 지역: ${ins.address}`);
  if (ins.occupation) lines.push(`  • 직업: ${ins.occupation}`);
  if (ins.memo) lines.push(`  • 메모: ${ins.memo}`);
  return lines.join("\n");
}

async function handleUpdate(name: string | null, fields: Record<string, unknown>, session: Session, fcId: string): Promise<string> {
  const resolvedName = name || session.last_customer_name;
  if (!resolvedName) return "❌ 고객 이름을 알려주세요.";

  const client = await resolveOne(resolvedName, session, "update", fields, fcId);
  if (typeof client === "string") return client;

  session.last_customer_name = client.name;
  session.last_customer_id = client.id;
  return handleUpdateById(client.id, client.name, fields, session);
}

async function handleUpdateById(id: string, name: string, fields: Record<string, unknown>, _session: Session): Promise<string> {
  const fm: Record<string, string> = {
    등급: "prospect_grade", 메모: "memo", 주소: "address", 지역: "address",
    직업: "occupation", 성별: "gender",
  };
  const upd: Record<string, unknown> = {};
  const log: string[] = [];

  for (const [f, v] of Object.entries(fields)) {
    const vStr = String(v);
    if (f === "나이") {
      const info = parseAge(vStr);
      if (info.age_group) upd.age_group = info.age_group;
      if (info.age !== null) upd.age = info.age;
      if (info.birth_year !== null) upd.birth_year = info.birth_year;
      log.push(`나이 → "${info.age_group || vStr}"`);
    } else {
      const col = fm[f] || f;
      upd[col] = vStr;
      log.push(`${f} → "${vStr}"`);
    }
  }

  if (!Object.keys(upd).length) return "❌ 수정할 항목이 없습니다.";
  const { error } = await supabase.from("clients").update(upd).eq("id", id);
  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${name}* 수정 완료\n${log.map(l => `  • ${l}`).join("\n")}`;
}

async function handleDelete(name: string | null, session: Session, fcId: string): Promise<string> {
  const resolvedName = name || session.last_customer_name;
  if (!resolvedName) return "❌ 삭제할 고객 이름을 알려주세요.";

  const client = await resolveOne(resolvedName, session, "delete", {}, fcId);
  if (typeof client === "string") return client;

  const { error } = await supabase.from("clients").delete().eq("id", client.id);
  if (error) return `❌ 삭제 실패: ${error.message}`;
  session.last_customer_name = "";
  session.last_customer_id = "";
  return `🗑️ *${client.name}* 삭제 완료`;
}

async function handleDeleteAll(name: string, fcId: string, session: Session): Promise<string> {
  if (!name) return "❌ 삭제할 고객 이름을 알려주세요.";
  const { data } = await supabase.from("clients").select("id, name").eq("fc_id", fcId).ilike("name", `%${name}%`);
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  const ids = data.map(c => c.id);
  const { error } = await supabase.from("clients").delete().in("id", ids);
  if (error) return `❌ 삭제 실패: ${error.message}`;
  session.last_customer_name = "";
  session.last_customer_id = "";
  return `🗑️ *${name}* ${data.length}명 전체 삭제 완료`;
}

async function handleContact(
  name: string | null,
  contactData: Record<string, unknown>,
  fcId: string,
  session: Session
): Promise<string> {
  const resolvedName = name || session.last_customer_name;
  if (!resolvedName) return "❌ 고객 이름을 알려주세요.";

  const client = await resolveOne(resolvedName, session, "contact", contactData, fcId);
  if (typeof client === "string") return client;

  session.last_customer_name = client.name;
  session.last_customer_id = client.id;

  const log: Record<string, unknown> = {
    fc_id: fcId,
    client_id: client.id,
    touch_method: contactData.touch_method || "",
    memo: contactData.memo || "",
    next_date: contactData.next_date || null,
    next_action: contactData.next_action || "",
  };

  const { error } = await supabase.from("contact_logs").insert(log);
  if (error) return `❌ 상담 기록 실패: ${error.message}`;

  const lines = [`📝 *${client.name}* 상담 기록 완료`];
  if (log.touch_method) lines.push(`  • 방법: ${log.touch_method}`);
  if (log.memo) lines.push(`  • 내용: ${log.memo}`);
  if (log.next_date) lines.push(`  • 다음: ${log.next_date} ${log.next_action || ""}`);
  return lines.join("\n");
}

async function handleVisit(
  name: string | null,
  visitData: Record<string, unknown>,
  fcId: string,
  session: Session
): Promise<string> {
  const resolvedName = name || session.last_customer_name;
  if (!resolvedName) return "❌ 고객 이름을 알려주세요.";

  const client = await resolveOne(resolvedName, session, "visit", visitData, fcId);
  if (typeof client === "string") return client;

  session.last_customer_name = client.name;
  session.last_customer_id = client.id;

  const log: Record<string, unknown> = {
    fc_id: fcId,
    client_id: client.id,
    touch_method: "방문예약",
    memo: visitData.memo || "",
    visit_reserved: true,
    visit_datetime: visitData.visit_datetime || null,
  };

  const { error } = await supabase.from("contact_logs").insert(log);
  if (error) return `❌ 방문 예약 실패: ${error.message}`;

  const dt = visitData.visit_datetime
    ? `\n  • 일시: ${String(visitData.visit_datetime).replace("T", " ").slice(0, 16)}`
    : "";
  const memo = visitData.memo ? `\n  • 메모: ${visitData.memo}` : "";
  return `📅 *${client.name}* 방문 예약 완료${dt}${memo}`;
}

async function handleSearch(params: Record<string, unknown>, fcId: string, session: Session): Promise<string> {
  let q = supabase.from("clients")
    .select("id, name, prospect_grade, age_group, address")
    .eq("fc_id", fcId);

  if (params.grade) q = q.eq("prospect_grade", String(params.grade).toUpperCase());
  if (params.address) q = q.ilike("address", `%${params.address}%`);
  if (params.keyword) q = q.or(`name.ilike.%${params.keyword}%,memo.ilike.%${params.keyword}%`);

  if (params.period === "today") {
    const today = new Date().toISOString().split("T")[0];
    q = q.gte("created_at", today);
  } else if (params.period === "week") {
    const week = new Date(Date.now() - 7 * 86400000).toISOString();
    q = q.gte("created_at", week);
  } else if (params.period === "month") {
    const month = new Date(Date.now() - 30 * 86400000).toISOString();
    q = q.gte("created_at", month);
  }

  const { data, error } = await q.order("created_at", { ascending: false }).limit(20);
  if (error) return `❌ 검색 실패: ${error.message}`;
  if (!data?.length) return "🔍 조건에 맞는 고객이 없습니다.";

  const lines = [`🔎 검색 결과 ${data.length}명\n`];
  data.forEach((c, i) => {
    const info = [c.prospect_grade ? `${c.prospect_grade}등급` : "", c.age_group, c.address].filter(Boolean).join(" / ");
    lines.push(`${i + 1}. *${c.name}* (${info || "-"})`);
  });

  if (data.length === 1) {
    session.last_customer_name = data[0].name;
    session.last_customer_id = data[0].id;
  }

  return lines.join("\n");
}

async function handleStats(params: Record<string, unknown>, fcId: string): Promise<string> {
  const type = String(params.type || "total");
  const lines = ["📊 *FCPilot 통계*\n"];

  if (type === "total" || type === "grade") {
    const { count: total } = await supabase.from("clients").select("id", { count: "exact", head: true }).eq("fc_id", fcId);
    lines.push(`고객 총 ${total || 0}명`);

    if (type === "grade") {
      for (const g of ["A", "B", "C", "D"]) {
        const { count } = await supabase.from("clients").select("id", { count: "exact", head: true })
          .eq("fc_id", fcId).eq("prospect_grade", g);
        if (count) lines.push(`  ${g}등급: ${count}명`);
      }
    }
  }

  if (type === "contact") {
    const month = new Date(Date.now() - 30 * 86400000).toISOString();
    const { count } = await supabase.from("contact_logs").select("id", { count: "exact", head: true })
      .eq("fc_id", fcId).gte("created_at", month);
    lines.push(`이번달 상담 ${count || 0}건`);
  }

  if (type === "pioneer") {
    const { count: shops } = await supabase.from("pioneer_shops").select("id", { count: "exact", head: true }).eq("fc_id", fcId);
    const { count: visits } = await supabase.from("pioneer_visits").select("id", { count: "exact", head: true }).eq("fc_id", fcId);
    lines.push(`개척 매장 ${shops || 0}개 / 방문 기록 ${visits || 0}건`);
  }

  return lines.join("\n");
}

async function handleReminder(fcId: string): Promise<string> {
  const today = new Date().toISOString().split("T")[0];
  const { data: logs } = await supabase
    .from("contact_logs")
    .select("client_id, next_date, next_action, clients(name, prospect_grade)")
    .eq("fc_id", fcId)
    .lte("next_date", today).not("next_date", "is", null)
    .order("next_date").limit(10);

  if (!logs?.length) return "✅ 오늘 예정된 리마인드가 없습니다.";

  const seen = new Set<string>();
  const lines = ["📋 *오늘의 할 일*\n"];
  for (const log of logs) {
    if (seen.has(log.client_id)) continue;
    seen.add(log.client_id);
    const c = (log.clients as Record<string, string>) || {};
    const icon = log.next_date < today ? "🔴" : "🟡";
    lines.push(`${icon} *${c.name || "?"}* [${c.prospect_grade || "-"}] — ${log.next_action || "연락"} (${log.next_date})`);
  }
  return lines.join("\n");
}

async function handleCommand(command: string, fcId: string): Promise<string> {
  const { error } = await supabase.from("command_queue").insert({ fc_id: fcId, command, status: "pending" });
  if (error) return `❌ 명령 저장 실패: ${error.message}`;
  return `📩 *명령 접수*\n\n"${command}"\n\nPC 켜져있으면 곧 실행됩니다.`;
}

async function handleSelect(num: number, session: Session, fcId: string): Promise<string> {
  if (!session.pending_selection.length) return "❌ 선택할 대상이 없습니다. 먼저 고객을 검색해주세요.";
  if (num < 1 || num > session.pending_selection.length)
    return `❌ 1~${session.pending_selection.length} 사이 번호를 선택해주세요.`;

  const sel = session.pending_selection[num - 1];
  session.last_customer_name = sel.name;
  session.last_customer_id = sel.id;

  const action = session.pending_action;
  const fields = session.pending_fields;
  session.pending_selection = [];
  session.pending_action = "";
  session.pending_fields = {};

  if (action === "update" && Object.keys(fields).length)
    return handleUpdateById(sel.id, sel.name, fields, session);
  if (action === "delete") {
    const { error } = await supabase.from("clients").delete().eq("id", sel.id);
    if (error) return `❌ 삭제 실패: ${error.message}`;
    session.last_customer_name = "";
    return `🗑️ *${sel.name}* 삭제 완료`;
  }
  if (action === "contact") {
    return handleContact(sel.name, fields as Record<string, unknown>, fcId, session);
  }
  if (action === "visit") {
    return handleVisit(sel.name, fields as Record<string, unknown>, fcId, session);
  }

  return `✅ *${sel.name}* 선택됨\n수정/삭제/상담기록 명령을 보내세요.`;
}

// ── 동명이인 처리 ───────────────────────────────────

async function resolveOne(
  name: string,
  session: Session,
  action = "",
  fields: Record<string, unknown> = {},
  fcId: string
): Promise<{ id: string; name: string } | string> {
  const { data } = await supabase
    .from("clients").select("id, name, prospect_grade, age_group, address")
    .eq("fc_id", fcId).ilike("name", `%${name}%`).limit(10);

  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;
  if (data.length === 1) return { id: data[0].id, name: data[0].name };

  session.pending_selection = data.map(c => ({
    id: c.id, name: c.name,
    info: [c.prospect_grade ? `${c.prospect_grade}등급` : "", c.age_group, c.address].filter(Boolean).join(" / "),
  }));
  session.pending_action = action;
  session.pending_fields = fields;

  const lines = [`👥 *"${name}"* ${data.length}명 발견\n`];
  data.forEach((c, i) => {
    const info = [c.prospect_grade ? `${c.prospect_grade}등급` : "", c.age_group, c.address].filter(Boolean).join(" / ");
    lines.push(`${i + 1}번: *${c.name}* (${info || "-"})`);
  });
  lines.push("\n번호를 선택해주세요.");
  return lines.join("\n");
}

// ── fc_id 조회 ──────────────────────────────────────

async function resolveFcId(chatId: string): Promise<string> {
  const { data: existing } = await supabase
    .from("users_settings").select("id").eq("telegram_chat_id", chatId).limit(1);
  if (existing?.length) return existing[0].id;

  const { data: anyUser } = await supabase.from("users_settings").select("id").limit(1);
  if (anyUser?.length) {
    await supabase.from("users_settings").update({ telegram_chat_id: chatId }).eq("id", anyUser[0].id);
    return anyUser[0].id;
  }

  const { data: authData, error: authErr } = await supabase.auth.admin.createUser({
    email: `fc_${chatId}@fcpilot.local`, password: crypto.randomUUID(),
    email_confirm: true, user_metadata: { display_name: "FC영민" },
  });
  if (authErr || !authData?.user) return "";
  const userId = authData.user.id;
  await new Promise(r => setTimeout(r, 500));
  await supabase.from("users_settings").update({ telegram_chat_id: chatId }).eq("id", userId);
  return userId;
}

// ── 메인 ────────────────────────────────────────────

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("OK");

  try {
    const body = await req.json();
    const msg = body?.message;
    if (!msg?.text) return new Response("OK");

    const chatId = String(msg.chat.id);
    if (chatId !== CHAT_ID) return new Response("OK");

    const fcId = await resolveFcId(chatId);
    if (!fcId) { await reply(chatId, "❌ 초기화 실패"); return new Response("OK"); }

    const session = await loadSession(chatId);
    const text = msg.text.trim();

    // 번호 선택 (pending 있을 때 숫자만 입력)
    if (session.pending_selection.length > 0) {
      const numMatch = text.match(/^(\d+)\s*번?$/);
      if (numMatch) {
        const response = await handleSelect(parseInt(numMatch[1]), session, fcId);
        await saveSession(chatId, session);
        await reply(chatId, response);
        return new Response("OK");
      }
    }

    const result = await callGemini(text, session);
    const action = String(result.action || "unknown");
    const name = result.name ? String(result.name) : null;

    let response: string;

    switch (action) {
      case "query":
        response = await handleQuery(name || "", session, fcId);
        break;
      case "register":
        response = await handleRegister((result.params as Record<string, unknown>) || {}, fcId, session);
        break;
      case "update":
        response = await handleUpdate(name, (result.fields as Record<string, unknown>) || {}, session, fcId);
        break;
      case "delete":
        response = await handleDelete(name, session, fcId);
        break;
      case "delete_all":
        response = await handleDeleteAll(name || "", fcId, session);
        break;
      case "reminder":
        response = await handleReminder(fcId);
        break;
      case "contact":
        response = await handleContact(name, (result.contact as Record<string, unknown>) || {}, fcId, session);
        break;
      case "visit":
        response = await handleVisit(name, (result.visit as Record<string, unknown>) || {}, fcId, session);
        break;
      case "command":
        response = await handleCommand(String(result.command || text), fcId);
        break;
      case "search":
        response = await handleSearch((result.params as Record<string, unknown>) || {}, fcId, session);
        break;
      case "stats":
        response = await handleStats((result.params as Record<string, unknown>) || {}, fcId);
        break;
      case "select":
        response = await handleSelect(Number((result.params as Record<string, unknown>)?.number || 0), session, fcId);
        break;
      case "rate_limited":
        response = "⏳ 잠시 후 다시 시도해주세요.";
        break;
      default:
        response = [
          "🤖 이해하지 못했습니다. 예시:",
          '• "양종학" → 조회',
          '• "홍길동 30대 B등급 서울 등록"',
          '• "등급 A로 변경" (직전 고객)',
          '• "오늘 양종학 통화함 관심있다고 함"',
          '• "양종학 내일 3시 방문"',
          '• "수원 A등급 고객 검색"',
          '• "고객 몇명이야?"',
          '• "할일"',
          '• "테스트해줘"',
        ].join("\n");
    }

    await saveSession(chatId, session);
    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
    try {
      await reply(CHAT_ID, `⚠️ 봇 오류: ${String(err).slice(0, 100)}`);
    } catch { /* ignore */ }
  }

  return new Response("OK");
});
