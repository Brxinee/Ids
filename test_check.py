"""
Quick detection test — run to verify if detection is working.
Expected:  kave.noft  → AVAILABLE,  instagram → TAKEN,  xyzfake99 → AVAILABLE
"""
import requests
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

s = requests.Session()

# Warm up session first
print("Warming up session...")
try:
    s.get(
        "https://www.instagram.com/",
        headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        },
        timeout=15,
    )
    print("Session ready. Waiting 3s...")
    time.sleep(3)
except Exception as e:
    print(f"Warm-up failed: {e}")

tests = [
    ("kave.noft",      "AVAILABLE"),
    ("instagram",      "TAKEN"),
    ("xyzfake99999x",  "AVAILABLE"),
]

for username, expected in tests:
    ua = random.choice(USER_AGENTS)
    r = s.get(
        f"https://www.instagram.com/{username}/",
        headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
        },
        timeout=15,
        allow_redirects=False,
    )
    location = r.headers.get("Location", "")
    print(f"--- {username} ---")
    print(f"  Status  : {r.status_code}")
    print(f"  Location: {location or '(none)'}")
    print(f"  Expected: {expected}")
    if r.status_code == 404:
        print(f"  Result  : AVAILABLE (404)")
    elif r.status_code in (301, 302, 303, 307, 308) and "accounts/login" in location:
        print(f"  Result  : TAKEN (redirect to login)")
    elif r.status_code == 429:
        print(f"  Result  : RATE LIMITED - try again later")
    elif r.status_code == 200:
        body = r.text[:100]
        print(f"  Result  : 200 OK - body: {body}")
    else:
        print(f"  Result  : UNKNOWN (status {r.status_code})")
    print()
    time.sleep(5)
