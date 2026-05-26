"""
Log into Instagram and save session for the hunter script.
Your password is never saved — only the session token is stored.
"""
import requests
import json
import getpass
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / "session.json"

s = requests.Session()
ua = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

print("=" * 50)
print("  Instagram Login — saves session token only")
print("  Your password is NOT stored anywhere.")
print("=" * 50)
print()

username = input("Instagram username: ").strip()
password = getpass.getpass("Instagram password (hidden): ").strip()

print("\nLogging in...")

try:
    # Step 1: Get CSRF token
    r = s.get("https://www.instagram.com/accounts/login/",
               headers={"User-Agent": ua}, timeout=15)
    csrf = s.cookies.get("csrftoken", "")

    # Step 2: Login
    r = s.post(
        "https://www.instagram.com/accounts/login/ajax/",
        data={
            "username":       username,
            "password":       password,
            "queryParams":    "{}",
            "optIntoOneTap":  "false",
        },
        headers={
            "User-Agent":       ua,
            "X-CSRFToken":      csrf,
            "X-Instagram-AJAX": "1",
            "X-Requested-With": "XMLHttpRequest",
            "Referer":          "https://www.instagram.com/accounts/login/",
            "Content-Type":     "application/x-www-form-urlencoded",
        },
        timeout=15,
    )

    data = r.json()

    if data.get("authenticated"):
        sessionid = s.cookies.get("sessionid", "")
        csrf2     = s.cookies.get("csrftoken", "")

        # Save session (NOT password)
        SESSION_FILE.write_text(json.dumps({
            "sessionid": sessionid,
            "csrftoken":  csrf2,
        }))

        print(f"\n✅ Login successful!")
        print(f"   Session saved to session.json")
        print(f"\nNow run:  python username_hunter.py")

    elif data.get("two_factor_required"):
        print("\n⚠️  Two-factor authentication required.")
        print("   Disable 2FA temporarily in Instagram settings, then retry.")

    elif data.get("checkpoint_required"):
        print("\n⚠️  Instagram wants to verify your account.")
        print("   Open Instagram app → approve the login → then retry.")

    else:
        print(f"\n❌ Login failed: {data}")

except Exception as e:
    print(f"\n❌ Error: {e}")
