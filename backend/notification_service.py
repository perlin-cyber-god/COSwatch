from telegram_client import send_dm

def notify_subscribers(supabase, asteroid_name: str, risk: float):
    res = (
        supabase.table("asteroid_subscriptions")
        .select("user_id")
        .eq("asteroid_name", asteroid_name)
        .execute()
    )

    for row in res.data or []:
        chat_id = int(row["user_id"])

        send_dm(
            chat_id,
            (
                f"🚨 Asteroid Alert\n\n"
                f"{asteroid_name} crossed risk threshold.\n"
                f"Risk score: {risk}\n\n"
                f"Check discussion thread for details."
            )
        )
