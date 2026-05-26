"""
Test Instagram username check using the signup endpoint.
Expected: kave.noft → AVAILABLE, instagram → TAKEN, xyzfake99999x → AVAILABLE
"""
import requests, time, random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

CHECK_URL  = "https://www.instagram.com/api/v1/web/accounts/check_username/"
SIGNUP_URL = "https://www.instagram.com/accounts/emailsignup/"

s = requests.Session()
ua = random.choice(USER_AGENTS)

print("Step 1: Getting CSRF token from homepage...")
s.get("https://www.instagram.com/", headers={"User-Agent": ua}, timeout=15)
time.sleep(2)

print("Step 2: Visiting signup page...")
s.get(SIGNUP_URL, headers={"User-Agent": ua, "Referer": "https://www.instagram.com/"}, timeout=15)
time.sleep(2)

csrf = s.cookies.get("csrftoken", "")
print(f"CSRF token: {csrf[:12]}...")
print()

for username, expected in [("kave.noft","AVAILABLE"),("instagram","TAKEN"),("xyzfake99999x","AVAILABLE")]:
    resp = s.post(
        CHECK_URL,
        data={"username": username},
        headers={
            "User-Agent":       ua,
            "Accept":           "*/*",
            "Content-Type":     "application/x-www-form-urlencoded",
            "X-CSRFToken":      csrf,
            "X-Instagram-AJAX": "1",
            "X-Requested-With": "XMLHttpRequest",
            "Referer":          SIGNUP_URL,
            "Origin":           "https://www.instagram.com",
        },
        timeout=15,
    )
    print(f"{username} (expected {expected})")
    print(f"  Status : {resp.status_code}")
    print(f"  Body   : {resp.text[:200]}")
    print()
    time.sleep(4)
