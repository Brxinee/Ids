"""
Check a specific list of handles against Instagram.
Uses your saved login session for reliable results.

Usage:
  python check_list.py
"""
import requests, time, random, json
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
SESSION_FILE = SCRIPT_DIR / "session.json"
PROFILE_API  = "https://www.instagram.com/api/v1/users/web_profile_info/?username={}"

UA = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

# ── HANDLES TO CHECK ──────────────────────────────────────────────────────
HANDLES = [
    # Claude's picks
    "losscraft","chartblind","tradedust","debtchaser","spikeborn",
    "sweatborn","grindghost","pulseforge","paincraft",
    "wronglaugh","jokeforge","clowncraft","laughdust",
    "riseblind","pushcraft","wakeblur","goalforge",
    "softgrind","voidbloom","quietforge","rawbloom",
    "stackblind","bugchaser","pingblind","buildcraft",
    "saltgrind","yolkbloom","spiceghost","brewblind",
    "glitchborn","bossblind","lagcraft","ragegrind",
    "trailforge","roadbloom","driftblind","fogchaser",
    "jugaadborn","jadoocraft","desigrind",
    # Your picks
    "yieldcrop","riskpulse","gainplot","chartmap",
    "ironpulse","flexpath","liftpace","formgrip",
    "gagshed","jokejunk","sighpost","laughsack",
    "mindspur","soulrise","soarlabs","aimcraft",
    "claysand","fawnsoft","duskglow","huespace",
    "bytecube","codehelm","hackport","launchpact",
    "zestyfork","herbchef","saltdish","biteslow",
    "questlog","playhaze","vidsport","plotgame",
    "mapdrift","camproam","wildpath","hikeclimb",
    "deshroute","yatrafilm","gyanflow","chaiplate",
]

# ─────────────────────────────────────────────────────────────────────────
session = requests.Session()

if not SESSION_FILE.exists():
    print("❌ No session.json found. Run login.py first.")
    exit(1)

saved = json.loads(SESSION_FILE.read_text())
session.cookies.set("sessionid", saved["sessionid"], domain=".instagram.com")
session.cookies.set("csrftoken",  saved["csrftoken"],  domain=".instagram.com")
print(f"✅ Session loaded ({saved['sessionid'][:8]}...)")
print(f"   Checking {len(HANDLES)} handles — ~{len(HANDLES)*15//60} mins\n")

available = []
taken     = []

for i, handle in enumerate(HANDLES, 1):
    for attempt in range(3):
        try:
            r = session.get(
                PROFILE_API.format(handle),
                headers={"User-Agent": random.choice(UA),
                         "x-ig-app-id": "936619743392459",
                         "Accept": "application/json",
                         "Referer": "https://www.instagram.com/"},
                timeout=15,
            )
            if r.status_code == 404:
                available.append(handle)
                print(f"  [{i:02d}/{len(HANDLES)}] ✅ AVAILABLE: @{handle}")
                break
            elif r.status_code == 200:
                user = r.json().get("data", {}).get("user")
                if user is None:
                    available.append(handle)
                    print(f"  [{i:02d}/{len(HANDLES)}] ✅ AVAILABLE: @{handle}")
                else:
                    taken.append(handle)
                    print(f"  [{i:02d}/{len(HANDLES)}] ❌ taken:     @{handle}")
                break
            elif r.status_code == 429:
                wait = 90 + random.uniform(0, 30)
                print(f"  [{i:02d}/{len(HANDLES)}] ⏳ Rate limited — sleeping {wait:.0f}s...")
                time.sleep(wait)
            else:
                taken.append(handle)
                print(f"  [{i:02d}/{len(HANDLES)}] ?  {r.status_code}: @{handle}")
                break
        except Exception as e:
            print(f"  [{i:02d}/{len(HANDLES)}] ?  error: @{handle} — {e}")
            time.sleep(5)
            break

    time.sleep(random.uniform(12, 18))  # safe delay between checks

print(f"\n{'='*50}")
print(f"✅ AVAILABLE ({len(available)}):")
for h in available:
    print(f"   @{h}")
print(f"\n❌ Taken: {len(taken)}")
print(f"{'='*50}")

# Save to file
out = Path("check_list_results.txt")
out.write_text(
    f"AVAILABLE ({len(available)}):\n" +
    "\n".join(f"  @{h}" for h in available) +
    f"\n\nTAKEN ({len(taken)}):\n" +
    "\n".join(f"  @{h}" for h in taken)
)
print(f"\nSaved to check_list_results.txt")
