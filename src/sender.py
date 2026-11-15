"""
sender.py - send (or simulate sending) emails and record them in the outreach log

Run from the project root:
    python src/sender.py

SIMULATE = True  -> no real email is sent; the tracker records "Sent (simulated)"
SIMULATE = False -> sends real email through Gmail SMTP
                    (.env needs SMTP_EMAIL and SMTP_APP_PASSWORD)
Instagram DMs are never sent automatically; they are marked "DM manual".
"""
import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from tracker import load_tracker, already_sent, log

ROOT = Path(__file__).resolve().parent.parent
MESSAGES_CSV = ROOT / "output" / "messages.csv"

SIMULATE = True
SENDER_NAME = "Ravi Kakkar"  # replaces the [Your Name] placeholder in each email
EMAIL_RE = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

load_dotenv(ROOT / ".env")


def send_email(to, subject, body):
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_APP_PASSWORD")
    if not sender or not password:
        raise RuntimeError("SMTP_EMAIL / SMTP_APP_PASSWORD are missing from .env")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)


def run(messages_df=None):
    if messages_df is None:
        messages_df = pd.read_csv(MESSAGES_CSV)

    tracker = load_tracker()
    counts = {"sent": 0, "skipped": 0, "duplicate": 0, "failed": 0}

    for _, row in messages_df.iterrows():
        email = str(row.get("email_to", "")).strip()
        pitch = row.get("email_pitch")
        gen_status = str(row.get("status", "OK"))

        # 1. The message was not generated
        if pd.isna(pitch) or gen_status.startswith("FAILED"):
            tracker = log(tracker, row, False, "Skipped: message missing")
            counts["skipped"] += 1
            continue

        # 2. No valid email, so only a manual DM is possible
        if not re.match(EMAIL_RE, email):
            tracker = log(tracker, row, False, "Skipped: no valid email (DM manual)")
            counts["skipped"] += 1
            continue

        # 3. Prevent duplicate outreach
        if already_sent(tracker, row["channel_id"], email):
            print("Duplicate skipped:", row["name"])
            counts["duplicate"] += 1
            continue

        body = str(pitch).replace("[Your Name]", SENDER_NAME)
        subject = f"Collaboration idea for {row['name']}"

        try:
            if SIMULATE:
                tracker = log(tracker, row, True, "Sent (simulated)")
            else:
                send_email(email, subject, body)
                tracker = log(tracker, row, True, "Sent")
            counts["sent"] += 1
        except Exception as e:
            tracker = log(tracker, row, False, f"Failed: {str(e)[:80]}")
            counts["failed"] += 1

    print("Summary:", counts)
    return tracker


if __name__ == "__main__":
    print(run().tail(10).to_string(index=False))