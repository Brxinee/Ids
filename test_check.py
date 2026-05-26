"""
Detection test — checks what Instagram actually returns for each case.
"""
import requests
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

s = requests.Session()

# Warm up
print("Warming up session...")
try:
    s.get("https://www.instagram.com/", headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=15)
    print("Ready. Waiting 3s...")
    time.sleep(3)
except Exception as e:
    print(f"Warm-up failed: {e}")

MARKERS_AVAILABLE = [
    "Sorry, this page isn’t available",
    "Sorry, this page isn't available",
    "Page Not Found",
    "page isn’t available",
    '"user_not_found"',
    '"UserNotFound"',
    '"errorCode":100',
    "The link you followed may be broken",
]
MARKERS_TAKEN = ['"is_private"', '"biography"', '"ProfilePage"', '"edge_followed_by"']
LOGIN_MARKERS = ["accounts/login", "loginForm", "Log in to Instagram"]

tests = [
    ("kave.noft",     "AVAILABLE"),
    ("instagram",     "TAKEN"),
    ("xyzfake99999x", "AVAILABLE"),
]

for username, expected in tests:
    r = s.get(
        f"https://www.instagram.com/{username}/",
        headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
        timeout=15,
        allow_redirects=False,
    )
    location = r.headers.get("Location", "")
    body = r.text

    avail_hit  = next((m for m in MARKERS_AVAILABLE if m in body), None)
    taken_hit  = next((m for m in MARKERS_TAKEN    if m in body), None)
    login_hit  = next((m for m in LOGIN_MARKERS    if m in body or m in location), None)

    print(f"\n--- {username} (expected: {expected}) ---")
    print(f"  Status        : {r.status_code}")
    print(f"  Location      : {location or '(none)'}")
    print(f"  Avail marker  : {avail_hit  or 'NOT FOUND'}")
    print(f"  Taken marker  : {taken_hit  or 'NOT FOUND'}")
    print(f"  Login marker  : {login_hit  or 'NOT FOUND'}")
    print(f"  Body (200chr) : {body[:200]}")

    time.sleep(5)
