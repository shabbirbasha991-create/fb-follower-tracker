import os
import re
import sys
import traceback
from datetime import datetime
from curl_cffi import requests

FB_SESSION = {
    "c_user": os.getenv("FB_C_USER"),
    "xs"    : os.getenv("FB_XS"),
    "datr"  : os.getenv("FB_DATR")
}

TARGET_URL = "https://www.facebook.com/share/19KA4vtZRM/"
WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL")


def post_to_sheets(payload):
    if not WEBHOOK_URL:
        raise ValueError("SHEET_WEBHOOK_URL secret is not set.")
    res = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    print(f"Sheet update response: {res.text}")


def run_facebook_checker():
    try:
        print(f"Connecting to target: {TARGET_URL}...")
        cookies = {k: v for k, v in FB_SESSION.items() if v}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }

        resp = requests.get(
            TARGET_URL,
            headers=headers,
            cookies=cookies,
            impersonate="chrome124",
            timeout=20,
            allow_redirects=True
        )

        html = resp.text
        final_url = resp.url
        print(f"Status: {resp.status_code} | Resolved URL: {final_url}")

        if "/checkpoint/" in final_url:
            print("Security checkpoint triggered. Browser login required.")
            sys.exit(1)

        def fmt(m):
            if not m:
                return "Unavailable"
            val = m.group(1).replace(",", "")
            return f"{int(val):,}" if val.isdigit() else m.group(1)

        followers_val = fmt(
            re.search(r'([0-9.,KkMm]+)\s+followers', html, re.IGNORECASE) or
            re.search(r'"follower_count":([0-9]+)', html) or
            re.search(r'Followed by\s+([0-9.,KkMm]+)\s+people', html, re.IGNORECASE)
        )

        following_val = fmt(
            re.search(r'([0-9.,KkMm]+)\s+following', html, re.IGNORECASE) or
            re.search(r'"following_count":([0-9]+)', html)
        )

        likes_val = fmt(
            re.search(r'([0-9.,KkMm]+)\s+likes', html, re.IGNORECASE) or
            re.search(r'"like_count":([0-9]+)', html) or
            re.search(r'([0-9.,KkMm]+)\s+people like this', html, re.IGNORECASE)
        )

        posts_val = fmt(
            re.search(r'([0-9.,KkMm]+)\s+posts', html, re.IGNORECASE) or
            re.search(r'"timeline_feed_units":\{"count":([0-9]+)\}', html)
        )

        now = datetime.now()
        data = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "followers": followers_val,
            "following": following_val,
            "likes": likes_val,
            "posts": posts_val
        }

        print(f"Logging data: {data}")
        post_to_sheets(data)

    except Exception:
        print("An error occurred:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_facebook_checker()
