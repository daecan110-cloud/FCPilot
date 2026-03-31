/**
 * FCPilot 매일 아침 리마인드 — Supabase Edge Function (cron)
 *
 * Supabase Dashboard → Database → Extensions → pg_cron 활성화 후:
 * SELECT cron.schedule('daily-reminder', '0 0 * * *',  -- UTC 0시 = KST 9시
 *   $$SELECT net.http_post(
 *     url := '<FUNCTION_URL>',
 *     headers := '{"Authorization": "Bearer <ANON_KEY>"}'::jsonb
 *   )$$
 * );
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function sendTelegram(text: string) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: CHAT_ID, text, parse_mode: "Markdown" }),
  });
}

Deno.serve(async () => {
  try {
    const today = new Date().toISOString().split("T")[0];

    // 상담 리마인드
    const { data: logs } = await supabase
      .from("contact_logs")
      .select("client_id, next_date, next_action, clients(name, prospect_grade)")
      .lte("next_date", today)
      .not("next_date", "is", null)
      .order("next_date")
      .limit(20);

    // 개척 팔로업 (방문 후 미재방문)
    const { data: shops } = await supabase
      .from("pioneer_shops")
      .select("shop_name, status, updated_at")
      .in("status", ["active", "visited"])
      .limit(20);

    const contactCount = logs?.length || 0;
    const pioneerCount = shops?.length || 0;
    const total = contactCount + pioneerCount;

    if (total === 0) return new Response("No reminders");

    const lines = [`☀️ *좋은 아침! 오늘의 할 일 (${total}건)*\n`];

    if (logs?.length) {
      const seen = new Set<string>();
      lines.push("*📞 상담 리마인드*");
      for (const log of logs) {
        if (seen.has(log.client_id)) continue;
        seen.add(log.client_id);
        const c = (log.clients as Record<string, string>) || {};
        const icon = log.next_date < today ? "🔴 지연" : "🟡 예정";
        lines.push(`  ${icon} *${c.name || "?"}* — ${log.next_action || "연락"}`);
      }
    }

    if (shops?.length) {
      lines.push("\n*🏪 개척 팔로업*");
      for (const s of shops) {
        lines.push(`  🟠 *${s.shop_name}* (${s.status === "visited" ? "방문완료" : "등록"})`);
      }
    }

    lines.push("\n_텔레그램에서 \"오늘 할 일\"로 상세 조회_");

    await sendTelegram(lines.join("\n"));
  } catch (err) {
    console.error("Error:", err);
  }

  return new Response("OK");
});
