/**
 * FCPilot 텔레그램 봇 — Supabase Edge Function
 *
 * 1단계: 로컬 키워드 매칭 (빠름, Gemini 호출 없음)
 * 2단계: Gemini 자연어 파싱 (애매한 경우만)
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

// ── 1단계: 로컬 키워드 매칭 ─────────────────────────

interface Intent {
  intent: string;
  params: Record<string, string>;
}

const REMINDER_KEYWORDS = [
  "할일", "할 일", "오늘", "리마인드", "일정", "예정", "뭐해", "뭐하지",
  "스케줄", "todo", "할거", "할 거",
];

const COMMAND_KEYWORDS = [
  "테스트", "git ", "push", "pull", "commit", "handoff", "배포", "빌드",
  "상태", "status",
];

const CREATE_KEYWORDS = [
  "새고객", "새 고객", "고객등록", "고객 등록", "신규고객", "신규 고객",
  "등록해", "등록해줘", "등록", "추가해", "추가해줘", "추가",
];

function extractCreateParams(text: string): Record<string, string> {
  // "김영민 등록해줘 시흥사는 20대" → {name: "김영민", address: "시흥", age: "20"}
  const t = text.replace(/\s+/g, " ").trim();

  // 키워드 제거하여 순수 정보만 남기기
  let cleaned = t;
  for (const k of ["새 고객", "새고객", "고객 등록", "고객등록", "신규 고객", "신규고객",
    "등록해줘", "등록해", "등록", "추가해줘", "추가해", "추가", ":", "："]) {
    cleaned = cleaned.replace(k, " ");
  }
  cleaned = cleaned.replace(/\s+/g, " ").trim();

  const params: Record<string, string> = {};

  // 이름 추출: 첫 번째 한글 2~4글자
  const nameMatch = cleaned.match(/([가-힣]{2,4})/);
  if (nameMatch) params.name = nameMatch[1];

  // 나이 추출: "20대", "30세", "45살" 등
  const ageMatch = cleaned.match(/(\d{1,3})\s*(대|세|살)/);
  if (ageMatch) params.age = ageMatch[1];

  // 주소 추출: "사는" 앞 단어, 또는 "서울/수원/시흥" 등
  const addrMatch = cleaned.match(/([가-힣]{2,10})\s*사는/) ||
    cleaned.match(/(서울|부산|대구|인천|광주|대전|울산|세종|수원|성남|시흥|용인|안양|고양|안산|화성|평택|의정부|파주|김포|제주|춘천|청주|전주|포항|창원|천안|구미|경주)/);
  if (addrMatch) params.address = addrMatch[1];

  // 메모: 남은 텍스트에서 추출 시도
  const memoMatch = cleaned.match(/메모\s*[:：]?\s*(.+)/);
  if (memoMatch) params.memo = memoMatch[1].trim();

  return params;
}

function localMatch(text: string): Intent | null {
  const t = text.replace(/\s+/g, " ").trim();
  const tNoSpace = t.replace(/\s/g, "");
  const tLower = t.toLowerCase();

  // 리마인드 — "할일", "오늘 할 일", "오늘할일", "뭐해" 등
  if (REMINDER_KEYWORDS.some((k) => tNoSpace.includes(k.replace(/\s/g, "")))) {
    return { intent: "reminder_list", params: {} };
  }

  // 고객 등록 — 로컬에서 직접 파라미터 추출
  if (CREATE_KEYWORDS.some((k) => tNoSpace.includes(k.replace(/\s/g, "")))) {
    const params = extractCreateParams(t);
    if (params.name) {
      return { intent: "customer_create", params };
    }
    return null; // 이름 추출 실패 시 Gemini 위임
  }

  // 개발 명령 — "테스트해줘", "git push", "handoff 업데이트"
  if (COMMAND_KEYWORDS.some((k) => tLower.includes(k))) {
    return { intent: "command", params: { command: t } };
  }

  // 고객 조회 — "김철수 고객정보", "김철수 정보", "김철수 조회"
  const searchPatterns = [
    /^(.{2,10})\s*(고객|정보|조회|검색|보여|찾아|알려)/,
    /^(고객|정보|조회)\s+(.{2,10})$/,
  ];
  for (const pat of searchPatterns) {
    const m = t.match(pat);
    if (m) {
      const name = (m[1] || m[2]).replace(/(고객|정보|조회|검색|보여|찾아|알려)/g, "").trim();
      if (name.length >= 2) return { intent: "customer_search", params: { name } };
    }
  }

  // 순수 한글 이름 2~4글자만 입력 → 고객 검색
  if (/^[가-힣]{2,4}$/.test(t)) {
    return { intent: "customer_search", params: { name: t } };
  }

  return null; // 매칭 안 됨 → Gemini에 위임
}

// ── 2단계: Gemini 자연어 파싱 ───────────────────────

async function geminiParse(text: string): Promise<Intent> {
  const prompt = `당신은 보험 FC(재무설계사) 업무 어시스턴트입니다.
사용자의 자연어 메시지를 분석하여 의도를 JSON으로 반환하세요.

## intent 종류와 예시

customer_search (고객 정보 조회):
  "김철수" → {"intent":"customer_search","params":{"name":"김철수"}}
  "김철수 고객" → 같음
  "김철수 정보 알려줘" → 같음
  "철수씨 보험 뭐 들었어?" → {"intent":"customer_search","params":{"name":"철수"}}

customer_create (새 고객 등록):
  "새 고객 홍길동 40대 서울" → {"intent":"customer_create","params":{"name":"홍길동","age":"40","address":"서울"}}
  "이영희 등록해줘 수원 사는 30대" → {"intent":"customer_create","params":{"name":"이영희","age":"30","address":"수원"}}

customer_update (고객 정보 수정):
  "김철수 등급 A로" → {"intent":"customer_update","params":{"name":"김철수","field":"등급","value":"A"}}
  "박영수 메모: VIP 고객" → {"intent":"customer_update","params":{"name":"박영수","field":"메모","value":"VIP 고객"}}

reminder_list (오늘 할 일 조회):
  "오늘 뭐해", "할일", "할 일", "일정", "스케줄", "리마인드" → {"intent":"reminder_list","params":{}}

reminder_done (리마인드 완료):
  "김철수 완료" → {"intent":"reminder_done","params":{"name":"김철수"}}

command (개발/PC 명령):
  "테스트해줘", "git push", "handoff 업데이트해" → {"intent":"command","params":{"command":"원문 그대로"}}

unknown: 위 어디에도 해당 안 되면

## 규칙
- 한국어 자연어를 유연하게 해석하세요
- 맞춤법 틀려도, 띄어쓰기 없어도, 줄임말이어도 최선을 다해 파악하세요
- JSON만 반환. 설명 없이. 코드 블록 없이.

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

// ── 의도 파악 (로컬 → Gemini 폴백) ─────────────────

async function resolveIntent(text: string): Promise<Intent> {
  const local = localMatch(text);
  if (local) return local;
  return await geminiParse(text);
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
    const { intent, params } = await resolveIntent(text);

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
        response = `🤖 이해하지 못했습니다.\n\n사용 예시:\n• "김철수" → 고객 조회\n• "할일" → 오늘 할 일\n• "새 고객: 이영희, 30대" → 등록\n• "테스트해줘" → PC 명령`;
    }

    await reply(chatId, response);
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
