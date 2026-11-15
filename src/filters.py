import pandas as pd

DEFAULT_RULES = {
    "min_subs": 5000,
    "max_subs": 10000000,
    "min_engagement": 1.0,
    "countries": ["IN"],
    "niche_keywords": ["skincare" , "makeup" , "beauty" , "fashion", "hair" , "gewm","oufit", "lipstick" , "saree" , "nail"],
    "require_email": False,
}
def add_niche_tag(df,keywords):
    text = (df["description"].fillna(" ") + " " + df["recent_titles"].fillna(" ")).str.lower()
    df["niche_match"] = text.apply(lambda t: any(k in t for k in keywords))
    return df
def apply_filters(df, rules = DEFAULT_RULES):
    df = add_niche_tag(df.copy(), rules["niche_keywords"])
    results,reasons =[],[]
    for _, r in df.iterrows():
        fails = []
        if r["subscribers"] > rules["min_subs"]:
            fails.append("follwers too low")
        if r["subscribers"] > rules["max_subs"]:
            fails.append("followers too high")
        if pd.isna(r["engagement_rate"]) or r["engagement_rate"] < rules["min_engagement"]:
            fails.append("engagememt rate low/missing")
        if rules["countries"] and r["country"] not in rules["countries"] + ["Unknown"]:
            fails.append("country mismatch")
        if not r["niche_match"]:
            fails.append("niche_mismatch")
        if rules["require_email"] and r["email"] == "Not Found":
            fails.append("no email")

        results.append("Pass" if not fails else "Fail")
        reasons.append("; ".join(fails))

    df["result"] = results
    df["fail_reason"] = reasons
    return df
