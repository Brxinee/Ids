"""
Log into Instagram and save session for the hunter script.
Uses only built-in Python — no extra packages needed.
Your password is never saved — only the session token is stored.
"""
import requests
import json
import uuid
import hmac
import hashlib
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / "session.json"

# Instagram's app signing key (public, used by all checkers)
IG_SIG_KEY = "9193488027538fd3450b83b7d05286d4ca8d7b1f9e76b57b8eeaea7e56f9872"
IG_APP_ID  = "567067343352427"
IG_UA      = ("Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; "
              "1080x1920; OnePlus; ONEPLUS A3003; OnePlus3; qcom; en_US; 314665256)")

def sign(data: dict) -> str:
    """Sign request data with Instagram's HMAC key."""
    body = json.dumps(data, separators=(",", ":"))
    sig  = hmac.new(IG_SIG_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"signed_body={sig}.{body}&ig_sig_key_version=4"

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
    # Step 1: get CSRF token
    r = s.get("https://www.instagram.com/", headers={"User-Agent": IG_UA}, timeout=15)
    csrf = s.cookies.get("csrftoken", "missing")

    # Step 2: login with signed request
    device_id = "android-" + hashlib.md5(username.encode()).hexdigest()[:16]
    guid      = str(uuid.uuid4())

    payload = sign({
        "_csrftoken":          csrf,
        "username":            username,
        "password":            password,
        "device_id":           device_id,
        "guid":                guid,
        "phone_id":            str(uuid.uuid4()),
        "login_attempt_count": 0,
        "_uuid":               guid,
    })

    r = s.post(
        "https://i.instagram.com/api/v1/accounts/login/",
        data=payload,
        headers={
            "User-Agent":           IG_UA,
            "Content-Type":         "application/x-www-form-urlencoded",
            "X-IG-App-ID":          IG_APP_ID,
            "X-IG-Capabilities":    "3brTvwM=",
            "X-IG-Connection-Type": "WIFI",
            "Accept-Language":      "en-US",
            "X-CSRFToken":          csrf,
        },
        timeout=15,
    )

    print(f"  Status: {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        if data.get("status") == "ok":
            sessionid = s.cookies.get("sessionid", "")
            csrf2     = s.cookies.get("csrftoken",  "")
            SESSION_FILE.write_text(json.dumps({
                "sessionid": sessionid,
                "csrftoken":  csrf2,
            }))
            print(f"\n✅ Login successful! Session saved.")
            print(f"\nNow run:  python username_hunter.py")
        else:
            msg = data.get("message", str(data))
            print(f"\n❌ Failed: {msg}")
            if "two_factor" in str(data):
                print("⚠️  Disable 2FA in Instagram app, then retry.")
            if "checkpoint" in str(data) or "challenge" in str(data):
                print("⚠️  Open Instagram app → approve the login → retry.")
    else:
        print(f"\n❌ Response: {r.text[:400]}")

except Exception as e:
    print(f"\n❌ Error: {e}")
