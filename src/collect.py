from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY
import re
import pandas as pd
youtube = build("youtube" , "v3" , developerKey = YOUTUBE_API_KEY)
KEYWORDS = ["skincare rutine india", "makeup tutorial india", "fashion haul india","grwm india","channel subscribers under 100000"]
def search_channel(KEYWORDS, max_results = 50):
    res = youtube.search().list(
    q = KEYWORDS,
    type = "channel",
    part = "snippet",
    maxResults=max_results,regionCode = "IN").execute()
    return [i["snippet"]["channelId"] for i in res["items"]]

def get_channel_details(ids):
    res = youtube.channels().list(
        part = "snippet, statistics,contentDetails", # name, description, country,subscribers,view,videocount,upload playlistID.
        id = ",".join(ids)).execute()
    rows = []
    for c in res["items"]:
        s = c["statistics"]
        rows.append({
            "channel_id": c["id"],
            "name": c["snippet"]["title"],
            "url":f"https://youtube.com/channel/{c['id']}",
            "country": c["snippet"].get("country"),
            "description": c["snippet"]["description"],
            "subscribers": int(s.get("subscriberCount",0)),
            "video_count": int(s.get("videoCount",0)),
            "total_view" : int(s.get("viewCount",0)),
            "uploads_id": c["contentDetails"]["relatedPlaylists"]["uploads"]
            })
    return rows
def get_recent_stats(uploads_id, n=10):
    pl = youtube.playlistItems().list(
        part = "contentDetails,snippet",playlistId = uploads_id,
        maxResults=n).execute()
    vids = [i["contentDetails"]["videoId"] for i in pl["items"]]
    titles = [i["snippet"]["title"] for i in pl["items"]]
    st = youtube.videos().list(part="statistics", id=",".join(vids)).execute()
    likes = sum(int(v["statistics"].get("likeCount",0)) for v in st["items"])
    comments = sum(int(v["statistics"].get("commentCount",0)) for v in st["items"])
    views = sum(int(v["statistics"].get("viewCount",0)) for v in st["items"])
    return {"recent_likes": likes, "recent_comments":comments,
    "recent_views": views, "recent_titles": " | " .join(titles)}

if __name__ == "__main__":
    ids = set()
    for kw in KEYWORDS:
        ids.update(search_channel(kw))
    ids = list(ids)[:100]
    rows = []
    for i in range(0, len(ids),50):
        rows += get_channel_details(ids[i:i+50])

    for r in rows:
        try:
            r.update(get_recent_stats(r["uploads_id"]))
        except Exception as e:
            print("skip:", r["name"], e)
    pd.DataFrame(rows).to_csv("data/raw_influencers.csv", index = False)
    print("saved", len(rows), "channels")
    


