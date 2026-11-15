"""
messages.py - Personalized email + Instagram DM generator (Gemini API)

Run from the project root:
    python src/messages.py

TEST_MODE = True  -> runs on the first 5 passing influencers only (saves quota)
TEST_MODE = False -> runs on all passing influencers
"""
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types


TEST_MODE = True
TEST_LIMIT = 5
MODEL = "gemini-flash-latest"   
MAX_RETRIES = 3                 
SLEEP_BETWEEN_CALLS = 4         
NICHE = "Fashion & Beauty"

ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "filtered_influencers.csv"
OUTPUT_CSV = ROOT / "output" / "messages.csv"

ANGLES = [
    "affiliate campaign",
    "UGC content creation",
    "sponsored collaboration",
    "brand ambassador program",
    "barter product collaboration",
]

PROMPT = """You write short, natural outreach messages to micro-influencers.

Influencer name: {name}
Niche: {niche}
Followers: {subs}
Recent video titles: {titles}
Collaboration angle: {angle}

Return ONLY a JSON object with exactly two keys: "email" and "dm".
- "email": 60 to 90 words. Friendly and specific. Mention one recent video or theme,
  the collaboration angle, and the value for the influencer. No subject line.
  End with a short sign-off using the placeholder [Your Name].
- "dm": 15 to 30 words. Short, casual, personalized to their content.
Do not invent facts about the influencer. Do not promise specific payment amounts."""

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit("GEMINI_API_KEY not found. Add GEMINI_API_KEY=... to your .env file.")

client = genai.Client(api_key=API_KEY)


def word_count(text):
    return len(str(text).split())


def counts_ok(email, dm):
    return 60 <= word_count(email) <= 90 and 15 <= word_count(dm) <= 30


def build_prompt(row, angle):
    titles = str(row.get("recent_titles", ""))[:300] or "not available"
    return PROMPT.format(
        name=row["name"],
        niche=NICHE,
        subs=int(row["subscribers"]),
        titles=titles,
        angle=angle,
    )


def generate(row, angle):
    """Return (email, dm, status). Status is OK, CHECK: <reason>, or FAILED: <reason>."""
    prompt = build_prompt(row, angle)
    best = (None, None)
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.8,
                ),
            )
            text = res.text.strip().replace("```json", "").replace("```", "")
            data = json.loads(text)
            email, dm = data["email"].strip(), data["dm"].strip()
            best = (email, dm)
            if counts_ok(email, dm):
                return email, dm, "OK"
            last_error = f"word count (email={word_count(email)}, dm={word_count(dm)})"
        except Exception as e:  
            last_error = str(e)[:120]
            print(f"   attempt {attempt} error: {last_error}")
            time.sleep(10)      
            continue
        time.sleep(SLEEP_BETWEEN_CALLS)

    if best[0]:
        return best[0], best[1], f"CHECK: {last_error}"
    return None, None, f"FAILED: {last_error}"


def generate_all(df):
    rows = []
    total = len(df)
    for i, (_, row) in enumerate(df.reset_index(drop=True).iterrows()):
        angle = ANGLES[i % len(ANGLES)]
        print(f"[{i + 1}/{total}] {row['name']} ({angle})")
        email, dm, status = generate(row, angle)
        print(f"   -> {status}")
        rows.append({
            "channel_id": row["channel_id"],
            "name": row["name"],
            "email_to": row.get("email", "Not Found"),
            "angle": angle,
            "email_pitch": email,
            "dm": dm,
            "status": status,
        })
        time.sleep(SLEEP_BETWEEN_CALLS)
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(INPUT_CSV)
    passed = df[df["result"] == "Pass"]
    print("Total rows:", len(df), "| Pass count:", len(passed))

    if passed.empty:
        raise SystemExit("No passing influencers found. Check the rules in filters.py first.")

    if TEST_MODE:
        passed = passed.head(TEST_LIMIT)
        print(f"TEST MODE: running on {len(passed)} influencers only\n")

    msgs = generate_all(passed)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    msgs.to_csv(OUTPUT_CSV, index=False)

    ok = (msgs["status"] == "OK").sum()
    print(f"\nDone: {ok}/{len(msgs)} generated without issues. Saved to {OUTPUT_CSV}")
    print(msgs[["name", "status"]].to_string(index=False))

    for _, r in msgs.head(2).iterrows():  # print two samples to read
        print("\n---", r["name"], "---")
        print("EMAIL:", r["email_pitch"])
        print("DM   :", r["dm"])


if __name__ == "__main__":
    main()