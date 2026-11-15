import re
import numpy as np
import pandas as pd
EMAIL_RE= r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
def add_engagement_rate(df):
    df["engagement_rate"] = (df["recent_likes"] + df["recent_comments"]) / df["recent_views"].replace(0,np.nan) *100
    return df

def extract_email(text):
    m = re.search(EMAIL_RE,str(text))
    return m.group(0) if m else "Not Found"
def add_email(df):
    df["email"] = df["description"].apply(extract_email)
    return df 
if __name__ == "__main__":
    df = pd.read_csv("data/raw_influencers.csv")
    df = add_email(add_engagement_rate(df))
    df.to_csv("data/processed_influencers.csv" , index= False)
    print(df.head())


