# Micro-Influencer Discovery & Outreach System

An end-to-end Python pipeline that discovers micro-influencers, filters and classifies them, enriches their profiles, generates personalized outreach messages with an LLM, simulates sending, and tracks every outreach.

```
Discovery -> Data Collection -> EDA & Features -> Filtering -> AI Personalization -> Sending -> Tracking
```

## Features

- **Discovery:** finds channels through keyword searches with the YouTube Data API v3.
- **EDA & feature engineering:** cleans the data, computes engagement rate, extracts public contact emails.
- **Filtering:** every influencer gets a clear `Pass` or `Fail` with the reason for failing.
- **Personalization:** the Gemini API writes a unique email (60-90 words) and Instagram DM (15-30 words) per influencer.
- **Sending layer:** sends or simulates emails, blocks duplicates, and keeps an outreach log.
- **Dashboard:** a Streamlit app with interactive filters, message generation, and the tracker.

## Tech Stack

| Area | Tools |
|---|---|
| Language | Python 3 |
| Data collection | YouTube Data API v3 (`google-api-python-client`) |
| Data processing & EDA | pandas, numpy, matplotlib, seaborn |
| AI personalization | Google Gemini API (`google-genai`) |
| Sending | `smtplib` (Gmail SMTP), simulation mode by default |
| Dashboard | Streamlit |
| Config | python-dotenv |

## Project Structure

```
Influencer_Outreach/
├── app.py                     # Streamlit dashboard
├── requirements.txt
├── README.md
├── .env                       # API keys (never commit this file)
├── data/
│   ├── raw_influencers.csv        # raw API output
│   ├── processed_influencers.csv  # after cleaning and feature engineering
│   └── filtered_influencers.csv   # with Pass/Fail and fail_reason
├── notebooks/
│   └── eda.ipynb              # exploratory data analysis
├── src/
│   ├── config.py              # loads API keys
│   ├── collect.py             # YouTube data collection
│   ├── featured.py            # engagement rate, email extraction, cleaning
│   ├── filters.py             # Pass/Fail logic
│   ├── messages.py            # Gemini message generation
│   ├── sender.py              # email sending / simulation
│   └── tracker.py             # outreach log and duplicate prevention
└── output/
    ├── charts/                # EDA charts
    ├── messages.csv           # generated emails and DMs
    └── outreach_tracker.csv   # outreach log
```

## How It Works

### 1. Data source and discovery
- Niche: **Fashion & Beauty (India)**.
- Several keyword searches (for example skincare, makeup, outfit and hair-care topics) return channel IDs, using `regionCode="IN"`.
- For each channel the pipeline fetches name, URL, country, description, subscribers, total views, video count, and the last 10 videos (titles, views, likes, comments).
- Total channels discovered: **[N]**. Micro-influencers (5,000-100,000 subscribers): **[N]**.

### 2. Cleaning and feature engineering
- Duplicate channels are removed.
- Missing `description` and `recent_titles` are filled with empty text; missing `country` becomes `Unknown`.
- **Engagement rate** = (likes + comments) / views x 100, over the last 10 videos. Zero-view channels and values above 100% are treated as invalid (`NaN`).
- **Email** is extracted from the public channel description with a regular expression. If none is found, the value is `Not Found`. Emails are never guessed or generated.

### 3. Filtering logic

| Rule | Default |
|---|---|
| Subscribers | 5,000 - 100,000 |
| Engagement rate | at least 1.5% (close to the dataset median) |
| Country | `IN` or `Unknown` |
| Niche | beauty/fashion keywords found in description or recent video titles |
| Email required | optional (off by default) |

Each influencer is labeled `Pass` or `Fail`, and `fail_reason` lists every rule that was not met. Failed influencers stay in the dataset so the classification is transparent.

### 4. AI personalization
- Model: Gemini (`gemini-flash-latest`) through the `google-genai` SDK.
- The prompt receives the influencer name, niche, follower count, recent video titles, and a rotating collaboration angle (affiliate, UGC, sponsored, brand ambassador, barter).
- The model returns JSON with an `email` (60-90 words) and a `dm` (15-30 words).
- Word counts are validated in code. If they are off, the request is retried up to 3 times; the final status is `OK`, `CHECK: ...`, or `FAILED: ...`.
- Placeholder `[Your Name]` is replaced with the sender name when emails are sent.

### 5. Sending layer
- Only influencers with a valid email address are selected.
- **Simulation mode is the default** (`SIMULATE = True` in `sender.py`): no real email leaves the machine, and the tracker records `Sent (simulated)`.
- Real sending uses Gmail SMTP with an app password (`SIMULATE = False`).
- Duplicates are prevented by `channel_id` and by email address.
- Instagram DMs are **generated only**. They are not sent automatically, because platform rules do not allow it; they are marked for manual sending.

### 6. Outreach tracker
`output/outreach_tracker.csv` records: influencer, email, message generated, sent, date, status.

## Setup

1. **Clone the repository and create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS / Linux
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** in the project root
   ```
   YOUTUBE_API_KEY=your_youtube_key
   GEMINI_API_KEY=your_gemini_key
   # Only needed for real sending:
   SMTP_EMAIL=your_gmail_address
   SMTP_APP_PASSWORD=your_gmail_app_password
   ```
   Get a YouTube key from Google Cloud Console and a free Gemini key from Google AI Studio.
4. **Run the pipeline**
   ```bash
   python src/collect.py        # collect data -> data/raw_influencers.csv
   # run notebooks/eda.ipynb to clean data and create processed_influencers.csv and filtered_influencers.csv
   python src/messages.py       # generate messages (test mode: first 5 influencers)
   python src/sender.py         # simulate sending and update the tracker
   streamlit run app.py         # open the dashboard
   ```
   In `src/messages.py`, set `TEST_MODE = False` to generate messages for all passing influencers.

## Limitations

- Most channels do not publish a public email, so many records show `Not Found`.
- Engagement rate is based on the last 10 videos only.
- Niche detection is keyword-based and can misclassify channels.
- Audience demographics (age, gender, geography) are not available through the public YouTube API.
- The YouTube API has a daily quota (10,000 units); each search call costs 100 units.
- The Gemini free tier is rate limited; the pipeline waits and retries, but large runs will be slow.
- Instagram and TikTok are not used because their official APIs restrict discovery and messaging.

## Responsible Use

- Only public data is collected, and no email addresses are guessed.
- Sending runs in simulation mode by default. Before any real outreach, respect each creator's preferences and applicable anti-spam and privacy rules.
- Never commit `.env` or any API key.

## Scalability

The pipeline is modular: each stage reads one CSV and writes the next. To scale from 50 to 500+ influencers, add more keywords or pagination in `collect.py`, run `messages.py` with `TEST_MODE = False`, and swap the CSV files for a database if needed. The LLM provider can be replaced by editing only the `generate()` function in `messages.py`.