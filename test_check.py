"""
Test the web_create_ajax endpoint — parses username errors from signup response.
Run this after airplane mode / waiting for rate limit to clear.
"""
import requests, time, random

UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
s = requests.Session()

print("Getting CSRF token...")
s.get("https://www.instagram.com/", headers={"User-Agent": UA}, timeout=15)
time.sleep(2)
s.get("https://www.instagram.com/accounts/emailsignup/", headers={"User-Agent": UA,
      "Referer": "https://www.instagram.com/"}, timeout=15)
csrf = s.cookies.get("csrftoken", "")
print(f"CSRF: {csrf[:12]}...")
print()

def check(username):
    r = s.post(
        "https://www.instagram.com/accounts/web_create_ajax/attempt/",
        data={
            "email":    f"test{random.randint(1000,9999)}@mailinator.com",
            "password": "Test@123456",
            "username": username,
            "first_name": "Test",
        },
        headers={
            "User-Agent":       UA,
            "X-CSRFToken":      csrf,
            "X-Instagram-AJAX": "1",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type":     "application/x-www-form-urlencoded",
            "Referer":          "https://www.instagram.com/accounts/emailsignup/",
            "Origin":           "https://www.instagram.com",
        },
        timeout=15,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body  : {r.text[:300]}")
    return r

for username, expected in [("instagram","TAKEN"),("kave.noft","AVAILABLE"),("xyzfake99999x","AVAILABLE")]:
    print(f"\n=== {username} (expected: {expected}) ===")
    check(username)
    time.sleep(5)
