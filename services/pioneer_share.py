"""개척 리스트 팀원 공유 서비스"""
from utils.helpers import safe_error


def get_all_users(supabase, my_id: str) -> list[dict]:
    """공유 대상으로 선택 가능한 사용자 목록 (본인 제외)"""
    try:
        res = (supabase.table("users_settings")
               .select("id, display_name")
               .neq("id", my_id)
               .order("display_name")
               .execute())
        return res.data or []
    except Exception:
        return []


def get_my_shares(supabase, my_id: str) -> list[dict]:
    """내가 공유한 사람 목록"""
    try:
        res = (supabase.table("pioneer_shares")
               .select("id, shared_with_id, created_at")
               .eq("owner_id", my_id)
               .order("created_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def get_shared_to_me(supabase, my_id: str) -> list[dict]:
    """나에게 공유된 사람 목록"""
    try:
        res = (supabase.table("pioneer_shares")
               .select("id, owner_id, created_at")
               .eq("shared_with_id", my_id)
               .order("created_at", desc=True)
               .execute())
        return res.data or []
    except Exception:
        return []


def create_share(supabase, owner_id: str, shared_with_id: str) -> tuple[bool, str]:
    """공유 생성"""
    try:
        supabase.table("pioneer_shares").insert({
            "owner_id": owner_id,
            "shared_with_id": shared_with_id,
        }).execute()
        return True, ""
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False, "이미 공유된 팀원입니다."
        return False, str(safe_error("공유", e))


def delete_share(supabase, share_id: str, my_id: str) -> tuple[bool, str]:
    """공유 해제 (owner 또는 shared_with 본인만 가능)"""
    try:
        supabase.table("pioneer_shares").delete().eq("id", share_id).execute()
        return True, ""
    except Exception as e:
        return False, str(safe_error("공유 해제", e))


def get_shared_shops(supabase, my_id: str) -> dict[str, list[dict]]:
    """나에게 공유된 매장들을 owner별로 그룹화하여 반환"""
    shares = get_shared_to_me(supabase, my_id)
    if not shares:
        return {}

    owner_ids = [s["owner_id"] for s in shares]
    result: dict[str, list[dict]] = {}

    for oid in owner_ids:
        try:
            res = (supabase.table("pioneer_shops")
                   .select("*")
                   .eq("fc_id", oid)
                   .order("created_at", desc=True)
                   .execute())
            if res.data:
                result[oid] = res.data
        except Exception:
            continue

    return result
