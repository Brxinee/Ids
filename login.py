"""
Log into Instagram via mobile API and save session for the hunter script.
Your password is never saved — only the session token is stored.
"""
import requests
import json
import uuid
import hashlib
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / "session.json"

print("=" * 50)
print("  Instagram Login")
print("  Your password is NOT stored anywhere.")
print("=" * 50)
print()

username = input("Instagram username: ").strip()
password = input("Instagram password: ").strip()

print("\nLogging in...")

device_id = "android-" + hashlib.md5(username.encode()).hexdigest()[:16]
uuid_val   = str(uuid.uuid4())

s  = requests.Session()
ua = "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; OnePlus; ONEPLUS A3003; OnePlus3; qcom; en_US; 314665256)"

try:
    # Step 1: get CSRF token from homepage
    r = s.get(
        "https://www.instagram.com/",
        headers={"User-Agent": ua},
        timeout=15,
    )
    csrf = s.cookies.get("csrftoken", "missing")

    # Step 2: login via mobile API (accepts plain password)
    r = s.post(
        "https://i.instagram.com/api/v1/accounts/login/",
        data={
            "_csrftoken":          csrf,
            "username":            username,
            "password":            password,
            "device_id":           device_id,
            "guid":                uuid_val,
            "login_attempt_count": "0",
        },
        headers={
            "User-Agent":          ua,
            "X-IG-App-ID":         "567067343352427",
            "X-IG-Capabilities":   "3brTvwM=",
            "X-IG-Connection-Type":"WIFI",
            "Content-Type":        "application/x-www-form-urlencoded",
            "Accept-Language":     "en-US",
        },
        timeout=15,
    )

    print(f"  Status: {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        if data.get("status") == "ok":
            sessionid = s.cookies.get("sessionid", "")
            csrf2     = s.cookies.get("csrftoken",  "")

            if not sessionid:
                # Try from response
                sessionid = data.get("logged_in_user", {}).get("session_id", "")

            SESSION_FILE.write_text(json.dumps({
                "sessionid": sessionid,
                "csrftoken":  csrf2,
            }))

            print(f"\n✅ Login successful!")
            print(f"   Saved to session.json")
            print(f"\nNow run:  python username_hunter.py")
        else:
            print(f"\n❌ Login failed: {data.get('message', data)}")
    else:
        body = r.text[:300]
        print(f"\n❌ Unexpected response: {body}")
        # Try parsing anyway
        try:
            data = r.json()
            msg = data.get("message") or data.get("error_type") or str(data)
            print(f"   Detail: {msg}")
            if "two_factor" in str(data):
                print("\n⚠️  2FA is ON — disable it in Instagram app settings, then retry.")
            if "checkpoint" in str(data):
                print("\n⚠️  Instagram wants to verify. Open the app → approve login → retry.")
        except Exception:
            pass

except Exception as e:
    print(f"\n❌ Error: {e}")
