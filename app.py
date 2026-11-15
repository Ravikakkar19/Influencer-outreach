"""
app.py - Streamlit dashboard

Run from the project root:
    streamlit run app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from filters import apply_filters, DEFAULT_RULES   # noqa: E402
import sender                                      # noqa: E402


try:
    import messages as msg_module
    GEMINI_READY = True
    GEMINI_ERR = ""
except (Exception, SystemExit) as e:
    msg_module = None
    GEMINI_READY = False
    GEMINI_ERR = str(e)

MESSAGES_CSV = ROOT / "output" / "messages.csv"
TRACKER_CSV = ROOT / "output" / "outreach_tracker.csv"

st.set_page_config(page_title="Influencer Outreach", layout="wide")
st.title("Micro-Influencer Discovery & Outreach")


@st.cache_data
def load_data():
    return pd.read_csv(ROOT / "data" / "processed_influencers.csv")


df = load_data()


st.sidebar.header("Filters")
min_subs, max_subs = st.sidebar.slider(
    "Subscribers", 0, 500000, (5000, 100000), step=1000)
min_eng = st.sidebar.slider("Minimum engagement %", 0.0, 10.0, 1.5, 0.1)
countries = st.sidebar.multiselect(
    "Country (empty = all)",
    sorted(df["country"].dropna().unique()), default=["IN"])
require_email = st.sidebar.checkbox("Only influencers with an email")

rules = DEFAULT_RULES.copy()
rules.update({"min_subs": min_subs, "max_subs": max_subs,
              "min_engagement": min_eng, "countries": countries,
              "require_email": require_email})

out = apply_filters(df, rules)

tab1, tab2, tab3 = st.tabs(["Influencers", "Messages", "Outreach tracker"])


with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(out))
    c2.metric("Pass", int((out["result"] == "Pass").sum()))
    c3.metric("Fail", int((out["result"] == "Fail").sum()))

    show = st.radio("Show", ["All", "Pass", "Fail"], horizontal=True)
    view = out if show == "All" else out[out["result"] == show]
    cols = ["name", "url", "subscribers", "engagement_rate", "country",
            "email", "result", "fail_reason"]
    st.dataframe(view[cols])
    st.download_button("Download CSV", view.to_csv(index=False),
                       "filtered_influencers.csv")


with tab2:
    st.subheader("Generate messages with Gemini")
    if not GEMINI_READY:
        st.warning(f"Gemini is not ready: {GEMINI_ERR}. "
                   "Check GEMINI_API_KEY in your .env file.")
    else:
        n = st.number_input("How many passing influencers?", 1, 50, 5)
        if st.button("Generate messages (Gemini)"):
            passed = out[out["result"] == "Pass"].head(int(n))
            if passed.empty:
                st.error("No passing influencers. Relax the filters.")
            else:
                with st.spinner("Generating messages..."):
                    msgs = msg_module.generate_all(passed)
                MESSAGES_CSV.parent.mkdir(parents=True, exist_ok=True)
                msgs.to_csv(MESSAGES_CSV, index=False)
                st.success(f"{len(msgs)} messages saved.")

    if MESSAGES_CSV.exists():
        msgs_df = pd.read_csv(MESSAGES_CSV)
        st.dataframe(msgs_df)

        st.subheader("Sending")
        mode = "SIMULATION (no real emails)" if sender.SIMULATE else "REAL SEND"
        st.caption(f"Mode: {mode}")
        if st.button("Run sender"):
            sender.run(msgs_df)
            st.success("Sender finished. Check the tracker tab.")
    else:
        st.info("messages.csv does not exist yet.")


with tab3:
    if TRACKER_CSV.exists() and TRACKER_CSV.stat().st_size > 0:
        st.dataframe(pd.read_csv(TRACKER_CSV))
    else:
        st.info("The tracker is empty for now.")