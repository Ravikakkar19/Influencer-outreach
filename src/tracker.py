"""
tracker.py - outreach log (output/outreach_tracker.csv)
Prevents duplicate outreach: the same channel_id or email is never marked "Sent" twice.
"""
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "output" / "outreach_tracker.csv"
COLS = ["channel_id", "influencer", "email", "message_generated",
        "sent", "date", "status"]


def load_tracker():
    if PATH.exists() and PATH.stat().st_size > 0:
        return pd.read_csv(PATH)
    return pd.DataFrame(columns=COLS)


def already_sent(tracker, channel_id, email=None):
    sent = tracker[tracker["sent"] == "Yes"]
    if (sent["channel_id"] == channel_id).any():
        return True
    if email and email != "Not Found":
        if (sent["email"].astype(str).str.lower() == str(email).lower()).any():
            return True
    return False


def log(tracker, row, sent, status):
    channel_id = row["channel_id"]

    # Avoid adding the same "Skipped" entry on every run
    if status.startswith("Skipped"):
        dup = tracker[(tracker["channel_id"] == channel_id) &
                      (tracker["status"] == status)]
        if not dup.empty:
            return tracker

    new = {
        "channel_id": channel_id,
        "influencer": row["name"],
        "email": row.get("email_to", "Not Found"),
        "message_generated": "Yes",
        "sent": "Yes" if sent else "No",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": status,
    }
    tracker = pd.concat([tracker, pd.DataFrame([new])], ignore_index=True)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tracker.to_csv(PATH, index=False)
    return tracker