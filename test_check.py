import requests

s = requests.Session()
r = s.get(
    "https://www.instagram.com/api/v1/users/web_profile_info/?username=kave.noft",
    headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "x-ig-app-id": "936619743392459",
        "Accept": "application/json",
        "Referer": "https://www.instagram.com/",
    },
    timeout=15,
    allow_redirects=True,
)
print("Status:", r.status_code)
print("Final URL:", r.url)
print("Body:", r.text[:500])
