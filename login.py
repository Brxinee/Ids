"""
Log into Instagram and save session for the hunter script.
Uses only built-in Python — no extra packages needed.
"""
import requests
import json
import time
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / "session.json"

UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")

print("=" * 50)
print("  Instagram Login")
print("  Your password is NOT stored.")
print("=" * 50)
print()

username = input("Instagram username: ").strip()
password = input("Instagram password: ").strip()
print("\nLogging in...")

s = requests.Session()

try:
    # Step 1: load login page to get cookies + CSRF
    s.get("https://www.instagram.com/", headers={"User-Agent": UA}, timeout=15)
    time.sleep(1)
    r = s.get("https://www.instagram.com/accounts/login/",
              headers={"User-Agent": UA}, timeout=15)
    csrf = s.cookies.get("csrftoken", "")
    print(f"  CSRF: {csrf[:10]}...")

    # Step 2: build enc_password (version 0 = plain, no RSA needed)
    ts          = int(time.time())
    enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{ts}:{password}"

    # jazoest = sum of ASCII values of CSRF token chars + 2
    jazoest = str(sum(ord(c) for c in csrf) + 2)

    # Step 3: POST login
    r = s.post(
        "https://www.instagram.com/accounts/login/ajax/",
        data={
            "username":             username,
            "enc_password":         enc_password,
            "queryParams":          "{}",
            "optIntoOneTap":        "false",
            "trustedDeviceRecords": "{}",
            "jazoest":              jazoest,
        },
        headers={
            "User-Agent":       UA,
            "X-CSRFToken":      csrf,
            "X-Instagram-AJAX": "1",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type":     "application/x-www-form-urlencoded",
            "Referer":          "https://www.instagram.com/accounts/login/",
            "Origin":           "https://www.instagram.com",
            "Accept":           "*/*",
        },
        timeout=15,
    )

    print(f"  Status: {r.status_code}")
    print(f"  Body  : {r.text[:300]}")

    if r.status_code == 200:
        data = r.json()
        if data.get("authenticated"):
            sessionid = s.cookies.get("sessionid", "")
            csrf2     = s.cookies.get("csrftoken",  "")
            SESSION_FILE.write_text(json.dumps({
                "sessionid": sessionid,
                "csrftoken":  csrf2,
            }))
            print(f"\n✅ Login successful! Session saved.")
            print(f"\nNow run:  python username_hunter.py")
        elif data.get("two_factor_required"):
            print("\n⚠️  2FA is ON. Disable it in Instagram app settings, then retry.")
        elif data.get("checkpoint_required"):
            print("\n⚠️  Open Instagram app → approve the login → then retry here.")
        else:
            print(f"\n❌ Failed: {data.get('message', data)}")
    else:
        print(f"\n❌ Unexpected status {r.status_code}")

except Exception as e:
    print(f"\n❌ Error: {e}")
