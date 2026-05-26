import requests

s = requests.Session()

# Test 1: HTML page WITHOUT following redirects
# - Existing profile should redirect (302) to login
# - Non-existing profile should return 404 or 200 with error
print("=== Test: kave.noft (should be AVAILABLE) ===")
r = s.get(
    "https://www.instagram.com/kave.noft/",
    headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    },
    timeout=15,
    allow_redirects=False,
)
print("Status:", r.status_code)
print("Location:", r.headers.get("Location", "no redirect"))
print("Body preview:", r.text[:200])

print()
print("=== Test: instagram (should be TAKEN) ===")
r2 = s.get(
    "https://www.instagram.com/instagram/",
    headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    },
    timeout=15,
    allow_redirects=False,
)
print("Status:", r2.status_code)
print("Location:", r2.headers.get("Location", "no redirect"))
print("Body preview:", r2.text[:200])
