/**
 * FCPilot 텔레그램 봇 — 100% Gemini 자연어 처리
 *
 * 모든 메시지 → Gemini API → 구조화 JSON → DB 처리
 * 직전 대화 고객명 세션 저장 (이름 생략 대응)
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID")!;
const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// ── 직전 고객 세션 (메모리) ─────────────────────────

let lastCustomerName = "";

// ── 텔레그램 응답 ──────────────────────────────────

async function reply(chatId: string, text: string) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "Markdown" }),
  });
}

// ── 나이 파싱 ───────────────────────────────────────

interface AgeInfo {
  age_group: string;
  age: number | null;
  birth_year: number | null;
}

function parseAge(input: string): AgeInfo {
  const t = input.trim();
  const currentYear = new Date().getFullYear();

  // "00년생", "2000년생"
  const birthMatch = t.match(/(\d{2,4})\s*년생/);
  if (birthMatch) {
    let year = parseInt(birthMatch[1]);
    if (year < 100) year += year <= (currentYear % 100) ? 2000 : 1900;
    const exactAge = currentYear - year;
    const decade = Math.floor(exactAge / 10) * 10;
    return { age_group: `${decade}대 (${exactAge}세)`, age: exactAge, birth_year: year };
  }

  // "26살", "36세"
  const exactMatch = t.match(/(\d{1,3})\s*(살|세)/);
  if (exactMatch) {
    const exactAge = parseInt(exactMatch[1]);
    const decade = Math.floor(exactAge / 10) * 10;
    return { age_group: `${decade}대 (${exactAge}세)`, age: exactAge, birth_year: currentYear - exactAge };
  }

  // "20대"
  const decadeMatch = t.match(/(\d{1,2})0?\s*대/);
  if (decadeMatch) {
    const decade = parseInt(decadeMatch[1]) * 10;
    return { age_group: `${decade}대`, age: decade, birth_year: null };
  }

  // 숫자만 ("36")
  const numOnly = t.match(/^(\d{1,3})$/);
  if (numOnly) {
    const n = parseInt(numOnly[1]);
    if (n >= 10 && n <= 99) {
      const decade = Math.floor(n / 10) * 10;
      return { age_group: `${decade}대 (${n}세)`, age: n, birth_year: currentYear - n };
    }
  }

  return { age_group: t, age: null, birth_year: null };
}

// ── Gemini API ──────────────────────────────────────

interface GeminiResult {
  action: "query" | "register" | "update" | "reminder" | "command" | "unknown";
  name?: string;
  fields?: Record<string, string>;
  params?: Record<string, string>;
}

async function callGemini(text: string): Promise<GeminiResult> {
  const systemPrompt = `너는 보험 FC(재무설계사) 업무 봇이다. 사용자 메시지를 분석해서 반드시 JSON만 응답해.

{
  "action": "query" | "register" | "update" | "reminder" | "command",
  "name": "고객 이름 (있으면)",
  "fields": { "수정할 필드": "값" },
  "params": { "등록 파라미터" }
}

## action별 규칙

query (고객 조회):
  "김철수" → {"action":"query","name":"김철수"}
  "김철수 고객 정보" → {"action":"query","name":"김철수"}
  "김철수 정보 알려줘" → {"action":"query","name":"김철수"}
  이름만 있고 다른 키워드 없으면 → query

register (고객 등록):
  "등록" 키워드 위치 상관없이 등록으로 처리
  "양종학 00년생 수원 등록" → {"action":"register","params":{"name":"양종학","age":"00년생","address":"수원"}}
  "등록 홍길동 40대 서울" → {"action":"register","params":{"name":"홍길동","age":"40대","address":"서울"}}
  "김영민 등록해줘 시흥 20대" → {"action":"register","params":{"name":"김영민","age":"20대","address":"시흥"}}
  키워드: 등록, 등록해줘, 추가, 새고객, 신규

update (고객 수정):
  "김철수 등급 B" → {"action":"update","name":"김철수","fields":{"등급":"B"}}
  "나이 36으로 변경" → {"action":"update","fields":{"나이":"36살"}} (이름 없으면 name 생략)
  "김철수 등급 B로 변경하고 나이 20대로 수정" → {"action":"update","name":"김철수","fields":{"등급":"B","나이":"20대"}}
  "김영민 지역 수원" → {"action":"update","name":"김영민","fields":{"주소":"수원"}}
  키워드: 변경, 수정, 바꿔, 으로

reminder (리마인드):
  "할일", "할 일", "오늘할일", "오늘 할 일", "뭐해", "일정", "스케줄", "오늘 뭐하지" → {"action":"reminder"}

command (개발/PC 명령):
  "테스트해줘", "git push", "handoff 업데이트", "배포" → {"action":"command","params":{"command":"원문 그대로"}}

## 나이 표기 규칙 (params.age 또는 fields.나이)
- "20대" → "20대" 그대로
- "00년생" → "00년생" 그대로
- "36살", "36세" → "36살" 그대로
- 숫자만 "36" → "36살"

## 중요
- JSON만 반환. 설명 없이. 코드블록 없이.
- 한국어 맞춤법 틀려도, 띄어쓰기 없어도, 줄임말이어도 최선을 다해 파악
- 이름이 메시지에 없으면 name 필드 생략 (직전 대화 고객에 적용됨)
- action을 판별할 수 없으면 "unknown"`;

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: `${systemPrompt}\n\n사용자 메시지: "${text}"` }] }],
          generationConfig: { temperature: 0, maxOutputTokens: 512 },
        }),
      },
    );
    const data = await res.json();
    const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return JSON.parse(raw.replace(/```json\n?/g, "").replace(/```/g, "").trim());
  } catch (e) {
    console.error("Gemini error:", e);
    return { action: "unknown" };
  }
}

// ── 핸들러 ──────────────────────────────────────────

async function handleQuery(name: string): Promise<string> {
  lastCustomerName = name;

  const { data, error } = await supabase
    .from("clients")
    .select("name, prospect_grade, age, age_group, birth_year, gender, occupation, address, memo")
    .ilike("name", `%${name}%`)
    .limit(5);

  if (error) return `❌ 조회 실패: ${error.message}`;
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  return data
    .map((c) => {
      let ageDisplay = "";
      if (c.age_group) {
        ageDisplay = c.age_group;
        if (c.birth_year) {
          const shortYear = String(c.birth_year).slice(-2);
          if (!ageDisplay.includes("년생")) ageDisplay += ` (${shortYear}년생)`;
        }
      } else if (c.age) {
        ageDisplay = `${c.age}세`;
      }
      const info = [ageDisplay, c.gender === "M" ? "남" : c.gender === "F" ? "여" : "", c.occupation, c.address]
        .filter(Boolean).join(" / ");
      const memo = c.memo ? `\n  메모: ${c.memo}` : "";
      return `👤 *${c.name}* [${c.prospect_grade || "-"}등급]\n  ${info}${memo}`;
    })
    .join("\n\n");
}

async function handleRegister(params: Record<string, string>, fcId: string): Promise<string> {
  const name = params.name;
  if (!name) return "❌ 고객 이름이 필요합니다.";

  lastCustomerName = name;

  const insertData: Record<string, unknown> = {
    fc_id: fcId,
    name,
    address: params.address || "",
    memo: params.memo || "",
    prospect_grade: params.grade || "C",
  };

  if (params.age) {
    const info = parseAge(params.age);
    insertData.age_group = info.age_group;
    if (info.age !== null) insertData.age = info.age;
    if (info.birth_year !== null) insertData.birth_year = info.birth_year;
  }

  const { error } = await supabase.from("clients").insert(insertData);
  if (error) return `❌ 등록 실패: ${error.message}`;

  const ageDisplay = insertData.age_group ? ` / ${insertData.age_group}` : "";
  const addrDisplay = params.address ? ` / ${params.address}` : "";
  return `✅ *${name}* 등록 완료 (C등급${ageDisplay}${addrDisplay})`;
}

async function handleUpdate(name: string, fields: Record<string, string>): Promise<string> {
  lastCustomerName = name;

  const fieldMap: Record<string, string> = {
    등급: "prospect_grade", 메모: "memo", 주소: "address",
    지역: "address", 나이: "age", 직업: "occupation",
  };

  const { data: clients } = await supabase
    .from("clients").select("id, name").ilike("name", `%${name}%`).limit(1);
  if (!clients?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  const clientName = clients[0].name;
  const clientId = clients[0].id;
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

  const { error } = await supabase.from("clients").update(updateData).eq("id", clientId);
  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${clientName}* 수정 완료\n${changeLog.map((c) => `  • ${c}`).join("\n")}`;
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
  const { error } = await supabase.from("command_queue").insert({
    fc_id: fcId, command, status: "pending",
  });
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

  const email = `fc_${chatId}@fcpilot.local`;
  const { data: authData, error: authErr } = await supabase.auth.admin.createUser({
    email, password: crypto.randomUUID(), email_confirm: true,
    user_metadata: { display_name: "FC영민", telegram_chat_id: chatId },
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
    if (!fcId) {
      await reply(chatId, "❌ 사용자 초기화 실패. 다시 시도해주세요.");
      return new Response("OK");
    }

    const text = msg.text.trim();

    // 100% Gemini 파싱
    const result = await callGemini(text);
    const action = result.action || "unknown";

    // 이름 없으면 직전 대화 고객 사용
    const name = result.name || lastCustomerName;

    let response: string;
    switch (action) {
      case "query":
        if (!name) { response = "❌ 고객 이름을 알려주세요."; break; }
        response = await handleQuery(name);
        break;
      case "register":
        response = await handleRegister(result.params || {}, fcId);
        break;
      case "update":
        if (!name) { response = "❌ 고객 이름을 알려주세요."; break; }
        response = await handleUpdate(name, result.fields || {});
        break;
      case "reminder":
        response = await handleReminder();
        break;
      case "command":
        response = await handleCommand(result.params?.command || text, fcId);
        break;
      default:
        response = `🤖 이해하지 못했습니다.\n\n사용 예시:\n• "김철수" → 조회\n• "양종학 00년생 수원 등록"\n• "등급 B로 변경" (직전 고객)\n• "할일" → 리마인드\n• "테스트해줘" → PC 명령`;
    }

    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
