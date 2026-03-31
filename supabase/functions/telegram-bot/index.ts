/**
 * FCPilot 텔레그램 봇 — Supabase Edge Function
 *
 * Webhook으로 메시지 수신 → Gemini 의도 파악 → DB 조회/등록/명령큐
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID")!;
const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// ── 텔레그램 응답 ──────────────────────────────────

async function reply(chatId: string, text: string) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "Markdown" }),
  });
}

// ── Gemini 의도 파악 ────────────────────────────────

interface Intent {
  intent: string;
  params: Record<string, string>;
}

async function parseIntent(text: string): Promise<Intent> {
  const prompt = `당신은 보험 FC 업무 어시스턴트입니다.
사용자 메시지의 의도를 JSON으로 반환하세요.

intent 종류:
- customer_search: 고객 정보 조회 (params: {name})
- customer_create: 새 고객 등록 (params: {name, age?, address?, memo?})
- customer_update: 고객 수정 (params: {name, field, value})
- reminder_list: 오늘 할 일 조회
- reminder_done: 리마인드 완료 (params: {name})
- command: 개발 명령 (params: {command}) — 테스트, git, handoff 등
- unknown: 판별 불가

JSON만 반환. 설명 없이.

메시지: "${text}"`;

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0, maxOutputTokens: 256 },
        }),
      },
    );
    const data = await res.json();
    const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    return JSON.parse(raw.replace(/```json\n?/g, "").replace(/```/g, "").trim());
  } catch {
    return { intent: "unknown", params: {} };
  }
}

// ── 핸들러 ──────────────────────────────────────────

async function searchCustomer(name: string): Promise<string> {
  const { data, error } = await supabase
    .from("clients")
    .select("name, prospect_grade, age, gender, occupation, address, memo")
    .ilike("name", `%${name}%`)
    .limit(5);

  if (error) return `❌ 조회 실패: ${error.message}`;
  if (!data?.length) return `🔍 "${name}" 고객을 찾을 수 없습니다.`;

  return data
    .map((c) => {
      const info = [
        c.age ? `${c.age}세` : "",
        c.gender === "M" ? "남" : c.gender === "F" ? "여" : "",
        c.occupation,
        c.address,
      ]
        .filter(Boolean)
        .join(" / ");
      const memo = c.memo ? `\n  메모: ${c.memo}` : "";
      return `👤 *${c.name}* [${c.prospect_grade || "-"}등급]\n  ${info}${memo}`;
    })
    .join("\n\n");
}

async function createCustomer(p: Record<string, string>): Promise<string> {
  if (!p.name) return "❌ 고객 이름이 필요합니다.";

  const fcId = await getFirstUserId();
  const { error } = await supabase.from("clients").insert({
    fc_id: fcId,
    name: p.name,
    age: p.age ? parseInt(p.age) : null,
    address: p.address || "",
    memo: p.memo || "",
    prospect_grade: "C",
  });

  if (error) return `❌ 등록 실패: ${error.message}`;
  return `✅ *${p.name}* 고객 등록 완료 (C등급)`;
}

async function updateCustomer(p: Record<string, string>): Promise<string> {
  if (!p.name || !p.field || !p.value) return "❌ 이름, 항목, 값이 필요합니다.";

  const fieldMap: Record<string, string> = {
    등급: "prospect_grade",
    메모: "memo",
    주소: "address",
    나이: "age",
    직업: "occupation",
  };
  const dbField = fieldMap[p.field] || p.field;

  const { data: clients } = await supabase
    .from("clients")
    .select("id")
    .ilike("name", `%${p.name}%`)
    .limit(1);

  if (!clients?.length) return `🔍 "${p.name}" 고객을 찾을 수 없습니다.`;

  const val = dbField === "age" ? parseInt(p.value) : p.value;
  const { error } = await supabase
    .from("clients")
    .update({ [dbField]: val })
    .eq("id", clients[0].id);

  if (error) return `❌ 수정 실패: ${error.message}`;
  return `✅ *${p.name}*의 ${p.field} → "${p.value}" 변경 완료`;
}

async function listReminders(): Promise<string> {
  const today = new Date().toISOString().split("T")[0];

  const { data: logs } = await supabase
    .from("contact_logs")
    .select("client_id, next_date, next_action, clients(name, prospect_grade)")
    .lte("next_date", today)
    .not("next_date", "is", null)
    .order("next_date")
    .limit(10);

  if (!logs?.length) return "✅ 오늘 예정된 리마인드가 없습니다.";

  const seen = new Set<string>();
  const lines = ["📋 *오늘의 할 일*\n"];

  for (const log of logs) {
    if (seen.has(log.client_id)) continue;
    seen.add(log.client_id);

    const c = (log.clients as Record<string, string>) || {};
    const icon = log.next_date < today ? "🔴" : "🟡";
    lines.push(
      `${icon} *${c.name || "?"}* [${c.prospect_grade || "-"}] — ${log.next_action || "연락"} (${log.next_date})`,
    );
  }

  return lines.join("\n");
}

async function queueCommand(command: string): Promise<string> {
  const fcId = await getFirstUserId();
  const { error } = await supabase.from("command_queue").insert({
    fc_id: fcId,
    command,
    status: "pending",
  });

  if (error) return `❌ 명령 저장 실패: ${error.message}`;
  return `📩 *명령 접수*\n\n"${command}"\n\nPC 켜져있으면 곧 실행됩니다.`;
}

async function getFirstUserId(): Promise<string> {
  const { data } = await supabase
    .from("users_settings")
    .select("id")
    .limit(1);
  return data?.[0]?.id || "";
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

    const text = msg.text.trim();
    const { intent, params } = await parseIntent(text);

    let response: string;
    switch (intent) {
      case "customer_search":
        response = await searchCustomer(params.name || text);
        break;
      case "customer_create":
        response = await createCustomer(params);
        break;
      case "customer_update":
        response = await updateCustomer(params);
        break;
      case "reminder_list":
        response = await listReminders();
        break;
      case "reminder_done":
        response = `✅ "${params.name}" 리마인드 완료 처리`;
        break;
      case "command":
        response = await queueCommand(params.command || text);
        break;
      default:
        response = `🤖 이해하지 못했습니다.\n\n사용 예시:\n• "김철수 고객 정보"\n• "오늘 할 일"\n• "새 고객: 이영희, 30대, 수원"\n• "테스트해줘"`;
    }

    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
