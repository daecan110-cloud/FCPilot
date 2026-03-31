/**
 * FCPilot 텔레그램 봇 v4 — DB 세션 + 동명이인 + 전체삭제
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

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
  pending_fields: Record<string, string>;
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
  const t = input.trim();
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

  return { age_group: t, age: null as number | null, birth_year: null as number | null };
}

// ── Gemini API ──────────────────────────────────────

async function callGemini(text: string, session: Session) {
  const ctx = session.last_customer_name
    ? `직전 대화 고객: "${session.last_customer_name}"`
    : "직전 대화 고객: 없음";

  const hasPending = session.pending_selection.length > 0
    ? `현재 ${session.pending_selection.length}명 선택 대기 중 (번호 입력 가능)`
    : "";

  const prompt = `너는 보험 FC 업무 봇이다. 사용자 메시지를 분석해서 반드시 JSON만 응답해.

${ctx}
${hasPending}

{
  "action": "query"|"register"|"update"|"delete"|"delete_all"|"reminder"|"command"|"select",
  "name": "고객 이름",
  "fields": {"필드":"값"},
  "params": {"파라미터"},
  "select": 번호
}

## action 규칙

query: 고객 조회. 이름만 있고 동작 키워드 없으면 query.
register: 고객 등록. 키워드: 등록/추가/새고객/신규/넣어 (위치 무관)
  params: name, age, grade, address, memo, occupation
update: 고객 수정. 키워드: 변경/수정/바꿔/으로/올려/내려
  fields: {"등급":"B","나이":"36살"} 등. 이름 없으면 name 생략(직전 고객)
delete: 고객 1명 삭제. 키워드: 삭제/빼줘/제거/지워
delete_all: 동명이인 전체 삭제. "전체삭제/다 삭제/전부 지워"
reminder: 할일/리마인드. "할일/오늘/뭐해/일정"
command: PC명령. "테스트/git/handoff/배포"
select: 번호 선택. "1","1번","2번" → {"action":"select","select":1}

## 자연어 매핑
"빼줘"=삭제, "올려줘"=등급변경, "넣어줘"=등록
"방금 거 삭제"=delete(이름 생략), "b로 올려"=update 등급 B

## 나이: 원문 그대로 전달. "23세"→"23세", "00년생"→"00년생", "20대"→"20대"
## JSON만. 설명X. 코드블록X.

메시지: "${text}"`;

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0, maxOutputTokens: 512 },
        }),
      },
    );
    const data = await res.json();
    const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    if (!raw) return { action: "unknown" };
    return JSON.parse(raw.replace(/```json\n?/g, "").replace(/```/g, "").trim());
  } catch (e) {
    console.error("Gemini:", e);
    return { action: "unknown" };
  }
}

// ── 핸들러 ──────────────────────────────────────────

async function handleQuery(name: string, session: Session): Promise<string> {
  const { data, error } = await supabase
    .from("clients")
    .select("id, name, prospect_grade, age, age_group, birth_year, gender, occupation, address, memo")
    .ilike("name", `%${name}%`).limit(10);

  if (error) return `❌ 조회 실패: ${error.message}`;
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  session.last_customer_name = data[0].name;
  session.last_customer_id = data[0].id;

  return data.map((c, i) => {
    let age = "";
    if (c.age_group) {
      age = c.age_group;
      if (c.birth_year) { const sy = String(c.birth_year).slice(-2); if (!age.includes("년생")) age += ` (${sy}년생)`; }
    } else if (c.age) age = `${c.age}세`;
    const info = [age, c.gender === "M" ? "남" : c.gender === "F" ? "여" : "", c.occupation, c.address].filter(Boolean).join(" / ");
    const memo = c.memo ? `\n  메모: ${c.memo}` : "";
    const num = data.length > 1 ? `${i + 1}. ` : "";
    return `${num}👤 *${c.name}* [${c.prospect_grade || "-"}등급]\n  ${info}${memo}`;
  }).join("\n\n");
}

async function handleRegister(params: Record<string, string>, fcId: string, session: Session): Promise<string> {
  const name = params.name;
  if (!name) return "❌ 고객 이름이 필요합니다.";

  const grade = (params.grade || params.prospect_grade || params["등급"] || "C").toUpperCase();
  const ins: Record<string, unknown> = {
    fc_id: fcId, name,
    address: params.address || params["주소"] || params["지역"] || "",
    memo: params.memo || params["메모"] || "",
    occupation: params.occupation || params["직업"] || "",
    prospect_grade: grade,
  };

  const ageRaw = params.age || params["나이"];
  if (ageRaw) {
    const info = parseAge(ageRaw);
    ins.age_group = info.age_group;
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

async function handleUpdate(name: string, fields: Record<string, string>, session: Session): Promise<string> {
  const client = await resolveOne(name, session);
  if (typeof client === "string") return client;

  session.last_customer_name = client.name;
  session.last_customer_id = client.id;

  const fm: Record<string, string> = { 등급: "prospect_grade", 메모: "memo", 주소: "address", 지역: "address", 직업: "occupation" };
  const upd: Record<string, unknown> = {};
  const log: string[] = [];

  for (const [f, v] of Object.entries(fields)) {
    if (f === "나이") {
      const info = parseAge(v);
      upd.age_group = info.age_group;
      if (info.age !== null) upd.age = info.age;
      if (info.birth_year !== null) upd.birth_year = info.birth_year;
      log.push(`나이 → "${info.age_group}"`);
    } else {
      upd[fm[f] || f] = v;
      log.push(`${f} → "${v}"`);
    }
  }

  if (!Object.keys(upd).length) return "❌ 수정할 항목이 없습니다.";
  const { error } = await supabase.from("clients").update(upd).eq("id", client.id);
  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${client.name}* 수정 완료\n${log.map(c => `  • ${c}`).join("\n")}`;
}

async function handleDelete(name: string, session: Session): Promise<string> {
  const client = await resolveOne(name, session);
  if (typeof client === "string") return client;

  const { error } = await supabase.from("clients").delete().eq("id", client.id);
  if (error) return `❌ 삭제 실패: ${error.message}`;
  session.last_customer_name = "";
  session.last_customer_id = "";
  return `🗑️ *${client.name}* 삭제 완료`;
}

async function handleDeleteAll(name: string, session: Session): Promise<string> {
  const fcId = await resolveFcId(CHAT_ID);
  const { data } = await supabase.from("clients").select("id, name").ilike("name", `%${name}%`);
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  const ids = data.map(c => c.id);
  const { error } = await supabase.from("clients").delete().in("id", ids);
  if (error) return `❌ 삭제 실패: ${error.message}`;
  session.last_customer_name = "";
  session.last_customer_id = "";
  return `🗑️ *${name}* ${data.length}명 전체 삭제 완료`;
}

async function handleSelect(num: number, session: Session): Promise<string> {
  if (!session.pending_selection.length) return "❌ 선택할 대상이 없습니다. 먼저 고객을 검색해주세요.";
  if (num < 1 || num > session.pending_selection.length) return `❌ 1~${session.pending_selection.length} 사이 번호를 선택해주세요.`;

  const sel = session.pending_selection[num - 1];
  session.last_customer_name = sel.name;
  session.last_customer_id = sel.id;

  const action = session.pending_action;
  const fields = session.pending_fields;
  session.pending_selection = [];
  session.pending_action = "";
  session.pending_fields = {};

  if (action === "update" && Object.keys(fields).length) {
    return await handleUpdateById(sel.id, sel.name, fields, session);
  }
  if (action === "delete") {
    const { error } = await supabase.from("clients").delete().eq("id", sel.id);
    if (error) return `❌ 삭제 실패: ${error.message}`;
    session.last_customer_name = "";
    return `🗑️ *${sel.name}* 삭제 완료`;
  }

  return `✅ *${sel.name}* 선택됨. 이제 수정/삭제 명령을 보내세요.`;
}

async function handleUpdateById(id: string, name: string, fields: Record<string, string>, session: Session): Promise<string> {
  const fm: Record<string, string> = { 등급: "prospect_grade", 메모: "memo", 주소: "address", 지역: "address", 직업: "occupation" };
  const upd: Record<string, unknown> = {};
  const log: string[] = [];

  for (const [f, v] of Object.entries(fields)) {
    if (f === "나이") {
      const info = parseAge(v);
      upd.age_group = info.age_group;
      if (info.age !== null) upd.age = info.age;
      if (info.birth_year !== null) upd.birth_year = info.birth_year;
      log.push(`나이 → "${info.age_group}"`);
    } else {
      upd[fm[f] || f] = v;
      log.push(`${f} → "${v}"`);
    }
  }

  const { error } = await supabase.from("clients").update(upd).eq("id", id);
  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${name}* 수정 완료\n${log.map(c => `  • ${c}`).join("\n")}`;
}

// ── 동명이인 처리: 1명이면 바로 반환, 여러명이면 선택 UI ──

async function resolveOne(name: string, session: Session, action = "", fields: Record<string, string> = {}): Promise<{ id: string; name: string } | string> {
  const { data } = await supabase
    .from("clients").select("id, name, prospect_grade, age_group, address")
    .ilike("name", `%${name}%`).limit(10);

  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;
  if (data.length === 1) return { id: data[0].id, name: data[0].name };

  // 동명이인 → 선택 UI + 세션 저장
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

async function handleReminder(): Promise<string> {
  const today = new Date().toISOString().split("T")[0];
  const { data: logs } = await supabase
    .from("contact_logs")
    .select("client_id, next_date, next_action, clients(name, prospect_grade)")
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

// ── fc_id ───────────────────────────────────────────

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

    // 번호 선택 체크 (세션에 pending 있을 때)
    if (session.pending_selection.length > 0) {
      const numMatch = text.match(/^(\d+)\s*번?$/);
      if (numMatch) {
        const response = await handleSelect(parseInt(numMatch[1]), session);
        await saveSession(chatId, session);
        await reply(chatId, response);
        return new Response("OK");
      }
    }

    const result = await callGemini(text, session);
    const action = result.action || "unknown";
    const name = result.name || session.last_customer_name;

    let response: string;
    switch (action) {
      case "query":
        response = name ? await handleQuery(name, session) : "❌ 고객 이름을 알려주세요.";
        break;
      case "register":
        response = await handleRegister(result.params || {}, fcId, session);
        break;
      case "update":
        if (!name) { response = "❌ 고객 이름을 알려주세요."; break; }
        response = await handleUpdate(name, result.fields || {}, session);
        break;
      case "delete":
        if (!name) { response = "❌ 삭제할 고객 이름을 알려주세요."; break; }
        response = await handleDelete(name, session);
        break;
      case "delete_all":
        if (!name) { response = "❌ 삭제할 고객 이름을 알려주세요."; break; }
        response = await handleDeleteAll(name, session);
        break;
      case "select":
        response = await handleSelect(result.select || 0, session);
        break;
      case "reminder":
        response = await handleReminder();
        break;
      case "command":
        response = await handleCommand(result.params?.command || text, fcId);
        break;
      default:
        response = `🤖 이해하지 못했습니다.\n\n• "김철수" → 조회\n• "양종학 23세 B등급 수원 등록"\n• "등급 A로 변경" (직전 고객)\n• "양종학 삭제" / "전체삭제"\n• "할일"\n• "테스트해줘"`;
    }

    await saveSession(chatId, session);
    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
