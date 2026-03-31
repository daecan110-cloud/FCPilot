/**
 * FCPilot 텔레그램 봇 v3 — 100% Gemini + 삭제 + 동명이인 + 세션
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID")!;
const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// ── 세션 (Edge Function 인스턴스 메모리) ────────────

let lastCustomerName = "";
let lastCustomerId = "";
let pendingSelection: Array<{ id: string; name: string }> = [];

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

interface GeminiResult {
  action: string;
  name?: string;
  fields?: Record<string, string>;
  params?: Record<string, string>;
  select?: number;
}

async function callGemini(text: string): Promise<GeminiResult> {
  const ctx = lastCustomerName ? `직전 대화 고객: "${lastCustomerName}"` : "직전 대화 고객: 없음";

  const prompt = `너는 보험 FC 업무 봇이다. 사용자 메시지를 분석해서 반드시 JSON만 응답해.

${ctx}

{
  "action": "query" | "register" | "update" | "delete" | "reminder" | "command" | "select",
  "name": "고객 이름",
  "fields": { "필드": "값" },
  "params": { "파라미터" },
  "select": 번호
}

## action 규칙

query: 고객 조회
  "김철수" → {"action":"query","name":"김철수"}
  "김철수 정보", "김철수 보여줘" → query
  이름만 있고 다른 동작 키워드 없으면 → query

register: 고객 등록
  키워드: 등록, 등록해줘, 추가, 새고객, 신규 (위치 무관)
  "양종학 23세 b등급 등록 수원거주" → {"action":"register","params":{"name":"양종학","age":"23세","grade":"B","address":"수원"}}
  "등록 홍길동 40대 서울" → {"action":"register","params":{"name":"홍길동","age":"40대","address":"서울"}}
  params에 name, age, grade, address, memo, occupation 가능

update: 고객 수정
  "김철수 등급 B" → {"action":"update","name":"김철수","fields":{"등급":"B"}}
  "나이 36살로 변경" → {"action":"update","fields":{"나이":"36살"}} (이름 생략 → 직전 고객)
  "김철수 b로 올려줘" → {"action":"update","name":"김철수","fields":{"등급":"B"}} (올려줘 = 등급 변경)
  복수: "등급 B 나이 20대" → {"action":"update","fields":{"등급":"B","나이":"20대"}}
  키워드: 변경, 수정, 바꿔, 으로, 올려, 내려

delete: 고객 삭제
  "양종학 삭제" → {"action":"delete","name":"양종학"}
  "방금 등록한 거 삭제" → {"action":"delete"} (이름 생략 → 직전 고객)
  "양종학 빼줘" → {"action":"delete","name":"양종학"}
  키워드: 삭제, 빼줘, 제거, 지워

reminder: 리마인드/할일
  "할일", "할 일", "오늘할일", "뭐해", "일정", "스케줄" → {"action":"reminder"}

command: PC/개발 명령
  "테스트해줘", "git push", "handoff", "배포" → {"action":"command","params":{"command":"원문"}}

select: 번호 선택 (동명이인 선택)
  "1", "1번", "2번" → {"action":"select","select":1}

## 나이 표기
"20대" → "20대", "00년생" → "00년생", "36살" → "36살", "23세" → "23세"
숫자만 → "살" 붙여서 "36" → "36살"

## 중요
- JSON만 반환. 설명X. 코드블록X.
- 이름 없으면 name 생략 (직전 고객 적용)
- 자연어 유연 해석: 맞춤법 오류, 줄임말, 비격식 전부 처리
- "빼줘"=삭제, "올려줘"=등급 변경, "넣어줘"=등록

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
    console.error("Gemini error:", e);
    return { action: "unknown" };
  }
}

// ── 고객 찾기 (동명이인 처리) ───────────────────────

async function findClient(name: string): Promise<
  { type: "one"; id: string; name: string } |
  { type: "multi"; clients: Array<{ id: string; name: string; info: string }> } |
  { type: "none" }
> {
  const { data } = await supabase
    .from("clients")
    .select("id, name, prospect_grade, age_group, address")
    .ilike("name", `%${name}%`)
    .limit(10);

  if (!data?.length) return { type: "none" };
  if (data.length === 1) return { type: "one", id: data[0].id, name: data[0].name };

  return {
    type: "multi",
    clients: data.map((c) => ({
      id: c.id,
      name: c.name,
      info: [c.prospect_grade ? `${c.prospect_grade}등급` : "", c.age_group, c.address].filter(Boolean).join(" / "),
    })),
  };
}

async function resolveClient(name: string): Promise<{ id: string; name: string } | string> {
  const result = await findClient(name);

  if (result.type === "none") return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  if (result.type === "one") {
    lastCustomerName = result.name;
    lastCustomerId = result.id;
    return { id: result.id, name: result.name };
  }

  // 동명이인
  pendingSelection = result.clients.map((c) => ({ id: c.id, name: c.name }));
  const lines = [`👥 *"${name}"* ${result.clients.length}명 발견\n`];
  result.clients.forEach((c, i) => {
    lines.push(`${i + 1}번: *${c.name}* (${c.info || "-"})`);
  });
  lines.push("\n번호를 선택해주세요.");
  return lines.join("\n");
}

// ── 핸들러 ──────────────────────────────────────────

async function handleQuery(name: string): Promise<string> {
  const { data, error } = await supabase
    .from("clients")
    .select("name, prospect_grade, age, age_group, birth_year, gender, occupation, address, memo")
    .ilike("name", `%${name}%`)
    .limit(5);

  if (error) return `❌ 조회 실패: ${error.message}`;
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  lastCustomerName = data[0].name;

  if (data.length > 1) {
    pendingSelection = data.map((c) => ({ id: "", name: c.name }));
  }

  return data
    .map((c, i) => {
      let ageDisplay = "";
      if (c.age_group) {
        ageDisplay = c.age_group;
        if (c.birth_year) {
          const sy = String(c.birth_year).slice(-2);
          if (!ageDisplay.includes("년생")) ageDisplay += ` (${sy}년생)`;
        }
      } else if (c.age) {
        ageDisplay = `${c.age}세`;
      }
      const info = [ageDisplay, c.gender === "M" ? "남" : c.gender === "F" ? "여" : "", c.occupation, c.address]
        .filter(Boolean).join(" / ");
      const memo = c.memo ? `\n  메모: ${c.memo}` : "";
      const num = data.length > 1 ? `${i + 1}. ` : "";
      return `${num}👤 *${c.name}* [${c.prospect_grade || "-"}등급]\n  ${info}${memo}`;
    })
    .join("\n\n");
}

async function handleRegister(params: Record<string, string>, fcId: string): Promise<string> {
  const name = params.name;
  if (!name) return "❌ 고객 이름이 필요합니다.";

  lastCustomerName = name;

  const grade = (params.grade || params.prospect_grade || params["등급"] || "C").toUpperCase();
  const insertData: Record<string, unknown> = {
    fc_id: fcId,
    name,
    address: params.address || params["주소"] || params["지역"] || "",
    memo: params.memo || params["메모"] || "",
    occupation: params.occupation || params["직업"] || "",
    prospect_grade: grade,
  };

  if (params.age || params["나이"]) {
    const info = parseAge(params.age || params["나이"]);
    insertData.age_group = info.age_group;
    if (info.age !== null) insertData.age = info.age;
    if (info.birth_year !== null) insertData.birth_year = info.birth_year;
  }

  const { data, error } = await supabase.from("clients").insert(insertData).select("id").single();
  if (error) return `❌ 등록 실패: ${error.message}`;

  lastCustomerId = data?.id || "";

  const parts = [`✅ *${name}* 등록 완료`];
  parts.push(`  • 등급: ${grade}`);
  if (insertData.age_group) parts.push(`  • 나이: ${insertData.age_group}`);
  if (insertData.address) parts.push(`  • 지역: ${insertData.address}`);
  if (insertData.occupation) parts.push(`  • 직업: ${insertData.occupation}`);
  if (insertData.memo) parts.push(`  • 메모: ${insertData.memo}`);
  return parts.join("\n");
}

async function handleUpdate(name: string, fields: Record<string, string>): Promise<string> {
  const resolved = await resolveClient(name);
  if (typeof resolved === "string") return resolved;

  lastCustomerName = resolved.name;
  lastCustomerId = resolved.id;

  const fieldMap: Record<string, string> = {
    등급: "prospect_grade", 메모: "memo", 주소: "address",
    지역: "address", 나이: "age", 직업: "occupation",
  };

  const updateData: Record<string, unknown> = {};
  const changeLog: string[] = [];

  for (const [field, value] of Object.entries(fields)) {
    if (field === "나이") {
      const info = parseAge(value);
      updateData.age_group = info.age_group;
      if (info.age !== null) updateData.age = info.age;
      if (info.birth_year !== null) updateData.birth_year = info.birth_year;
      changeLog.push(`나이 → "${info.age_group}"`);
    } else {
      const dbField = fieldMap[field] || field;
      updateData[dbField] = value;
      changeLog.push(`${field} → "${value}"`);
    }
  }

  if (!Object.keys(updateData).length) return "❌ 수정할 항목이 없습니다.";

  const { error } = await supabase.from("clients").update(updateData).eq("id", resolved.id);
  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${resolved.name}* 수정 완료\n${changeLog.map((c) => `  • ${c}`).join("\n")}`;
}

async function handleDelete(name: string): Promise<string> {
  const resolved = await resolveClient(name);
  if (typeof resolved === "string") return resolved;

  const { error } = await supabase.from("clients").delete().eq("id", resolved.id);
  if (error) return `❌ 삭제 실패: ${error.message}`;

  lastCustomerName = "";
  lastCustomerId = "";
  return `🗑️ *${resolved.name}* 삭제 완료`;
}

async function handleSelect(num: number): Promise<string> {
  if (!pendingSelection.length) return "❌ 선택할 대상이 없습니다. 먼저 고객을 검색해주세요.";
  if (num < 1 || num > pendingSelection.length) return `❌ 1~${pendingSelection.length} 사이 번호를 선택해주세요.`;

  const selected = pendingSelection[num - 1];
  lastCustomerName = selected.name;
  lastCustomerId = selected.id;
  pendingSelection = [];
  return `✅ *${selected.name}* 선택됨. 이제 수정/삭제 명령을 보내세요.`;
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

// ── fc_id 확보 ──────────────────────────────────────

async function resolveFcId(chatId: string): Promise<string> {
  const { data: existing } = await supabase
    .from("users_settings").select("id").eq("telegram_chat_id", chatId).limit(1);
  if (existing?.length) return existing[0].id;

  const { data: anyUser } = await supabase
    .from("users_settings").select("id").limit(1);
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
  await new Promise((r) => setTimeout(r, 500));
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

    const text = msg.text.trim();
    const result = await callGemini(text);
    const action = result.action || "unknown";
    const name = result.name || lastCustomerName;

    let response: string;
    switch (action) {
      case "query":
        response = name ? await handleQuery(name) : "❌ 고객 이름을 알려주세요.";
        break;
      case "register":
        response = await handleRegister(result.params || {}, fcId);
        break;
      case "update":
        response = name
          ? await handleUpdate(name, result.fields || {})
          : "❌ 고객 이름을 알려주세요.";
        break;
      case "delete":
        response = name ? await handleDelete(name) : "❌ 삭제할 고객 이름을 알려주세요.";
        break;
      case "select":
        response = await handleSelect(result.select || 0);
        break;
      case "reminder":
        response = await handleReminder();
        break;
      case "command":
        response = await handleCommand(result.params?.command || text, fcId);
        break;
      default:
        response = `🤖 이해하지 못했습니다.\n\n• "김철수" → 조회\n• "양종학 23세 B등급 수원 등록"\n• "등급 A로 변경" (직전 고객)\n• "양종학 삭제"\n• "할일"\n• "테스트해줘"`;
    }

    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
