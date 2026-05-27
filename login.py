"""
Log into Instagram using instagrapi and save session for the hunter script.
Your password is never saved — only the session token is stored.
"""
import json
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / "session.json"

try:
    from instagrapi import Client
except ImportError:
    print("Installing instagrapi...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "instagrapi"])
    from instagrapi import Client

print("=" * 50)
print("  Instagram Login")
print("  Your password is NOT stored anywhere.")
print("=" * 50)
print()

username = input("Instagram username: ").strip()
password = input("Instagram password: ").strip()

print("\nLogging in...")

try:
    cl = Client()
    cl.login(username, password)

    sessionid = cl.sessionid
    csrf      = cl.cookie_dict.get("csrftoken", "")

    SESSION_FILE.write_text(json.dumps({
        "sessionid": sessionid,
        "csrftoken":  csrf,
    }))

    print(f"\n✅ Login successful!")
    print(f"   Session saved to session.json")
    print(f"\nNow run:  python username_hunter.py")

except Exception as e:
    err = str(e).lower()
    if "two_factor" in err or "2fa" in err:
        print("\n⚠️  2FA is ON — disable it in Instagram app settings, then retry.")
    elif "checkpoint" in err or "challenge" in err:
        print("\n⚠️  Instagram wants to verify. Open Instagram app → approve login → retry.")
    elif "bad_password" in err or "invalid" in err:
        print("\n❌ Wrong username or password. Try again.")
    else:
        print(f"\n❌ Login failed: {e}")
