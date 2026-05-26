"""
Quick detection test — run after rate limit clears (wait 20 min first).
Expected:  kave.noft  → AVAILABLE,  instagram → TAKEN,  xyzfake99 → AVAILABLE
"""
import requests
import time

s = requests.Session()

tests = [
    ("kave.noft",      "AVAILABLE"),
    ("instagram",      "TAKEN"),
    ("xyzfake99999x",  "AVAILABLE"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

for username, expected in tests:
    r = s.get(
        f"https://www.instagram.com/{username}/",
        headers=headers,
        timeout=15,
        allow_redirects=False,
    )
    location = r.headers.get("Location", "")
    print(f"--- {username} ---")
    print(f"  Status  : {r.status_code}")
    print(f"  Location: {location or '(none)'}")
    print(f"  Expected: {expected}")
    if r.status_code == 404:
        print(f"  Result  : ✅ AVAILABLE (404)")
    elif r.status_code in (301,302,303,307,308) and "accounts/login" in location:
        print(f"  Result  : ❌ TAKEN (redirect to login)")
    elif r.status_code == 429:
        print(f"  Result  : ⏳ RATE LIMITED — wait longer then retry")
    else:
        print(f"  Result  : ❓ UNKNOWN (status {r.status_code})")
    print()
    time.sleep(4)
