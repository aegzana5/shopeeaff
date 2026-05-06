"""
One-time setup: open a real browser, let user log into Instagram via Facebook,
then save browser state for headless automation.

Run: python3 setup_instagram.py
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE_FILE = Path("assets/browser_state.json")
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def main():
    print("Opening browser for Instagram login...")
    print("1. Click 'Log in with Facebook'")
    print("2. Complete Facebook login in the browser window")
    print("3. Once you see the Instagram home feed, come back here and press Enter")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,          # visible browser
            channel="chromium",
            args=["--start-maximized"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")

        print("Browser opened. Complete login in the window...")
        print("Press Enter here when you see the Instagram home feed.")
        input()

        # Check we're logged in
        current_url = page.url
        if "instagram.com" in current_url and "login" not in current_url:
            ctx.storage_state(path=str(STATE_FILE))
            print(f"Session saved to {STATE_FILE}")
            print("Setup complete! You can now run the bot.")
        else:
            print(f"Warning: still on login page ({current_url}).")
            print("Try again after completing Facebook login.")

        browser.close()


if __name__ == "__main__":
    main()
