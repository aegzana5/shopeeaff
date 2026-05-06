"""
Auto-login to Shopee and save session cookies.
Run once; session lasts ~30 days.
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIES_FILE = Path("assets/shopee_cookies.json")
COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)

SHOPEE_USER = "tanakornaeg"
SHOPEE_PASS = "BSIhdw19"


def login_and_save():
    print("Logging into Shopee...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(
            locale="th-TH",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = ctx.new_page()
        page.goto("https://shopee.co.th/buyer/login", timeout=30000)
        time.sleep(2)

        # Fill username
        page.fill('input[name="loginKey"]', SHOPEE_USER)
        time.sleep(0.8)

        # Fill password
        page.fill('input[name="password"]', SHOPEE_PASS)
        time.sleep(0.8)

        # Click the "เข้าสู่ระบบ" (Login) button specifically
        page.click('button.b5aVaf')
        print("Submitted login form. Waiting for redirect...")

        try:
            # Wait for redirect away from login page (up to 60s for any CAPTCHA)
            page.wait_for_url(
                lambda url: "shopee.co.th" in url and "/login" not in url,
                timeout=60000,
            )
            print("Login successful!")
        except Exception:
            print("Auto-login timed out. If CAPTCHA appeared, solve it in the browser window.")
            print("Waiting 60 more seconds for manual solve...")
            page.wait_for_url(
                lambda url: "shopee.co.th" in url and "/login" not in url,
                timeout=60000,
            )

        cookies = ctx.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"✓ Saved {len(cookies)} cookies to {COOKIES_FILE}")
        browser.close()


if __name__ == "__main__":
    login_and_save()
    print("\nDone. Run: python3 main.py")
