"""
Test multiple Instagram endpoints to find which one works.
"""
import requests, time, random

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]
MOBILE_UA = "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; OnePlus; ONEPLUS A3003; OnePlus3; qcom; en_US; 314665256)"

s = requests.Session()
ua = USER_AGENTS[0]

# Get CSRF token
print("Getting CSRF token...")
s.get("https://www.instagram.com/", headers={"User-Agent": ua}, timeout=15)
time.sleep(2)
s.get("https://www.instagram.com/accounts/emailsignup/", headers={"User-Agent": ua}, timeout=15)
csrf = s.cookies.get("csrftoken", "")
print(f"CSRF: {csrf[:10]}...")
print()

username = "instagram"  # known TAKEN — good for testing

# Test 1: web check_username (old path)
print("=== Test 1: POST /api/v1/web/accounts/check_username/ ===")
r = s.post("https://www.instagram.com/api/v1/web/accounts/check_username/",
    data={"username": username},
    headers={"User-Agent": ua, "X-CSRFToken": csrf, "X-Instagram-AJAX": "1",
             "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.instagram.com/accounts/emailsignup/",
             "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
print(f"Status: {r.status_code} | Body: {r.text[:150]}")
print()
time.sleep(3)

# Test 2: without "web/"
print("=== Test 2: POST /api/v1/accounts/check_username/ ===")
r = s.post("https://www.instagram.com/api/v1/accounts/check_username/",
    data={"username": username},
    headers={"User-Agent": ua, "X-CSRFToken": csrf, "X-Instagram-AJAX": "1",
             "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.instagram.com/accounts/emailsignup/",
             "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
print(f"Status: {r.status_code} | Body: {r.text[:150]}")
print()
time.sleep(3)

# Test 3: mobile API subdomain
print("=== Test 3: GET i.instagram.com /api/v1/users/lookup/ ===")
r = requests.get(f"https://i.instagram.com/api/v1/users/lookup/?q={username}",
    headers={"User-Agent": MOBILE_UA, "X-IG-App-ID": "567067343352427",
             "Accept-Language": "en-US"}, timeout=15)
print(f"Status: {r.status_code} | Body: {r.text[:150]}")
print()
time.sleep(3)

# Test 4: signup attempt endpoint
print("=== Test 4: POST /accounts/web_create_ajax/attempt/ ===")
r = s.post("https://www.instagram.com/accounts/web_create_ajax/attempt/",
    data={"username": username, "email": "test@test.com", "password": "test123"},
    headers={"User-Agent": ua, "X-CSRFToken": csrf, "X-Instagram-AJAX": "1",
             "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.instagram.com/accounts/emailsignup/",
             "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
print(f"Status: {r.status_code} | Body: {r.text[:200]}")
