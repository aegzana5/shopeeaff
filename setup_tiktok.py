"""
One-time setup: open browser, log into TikTok, save session.
Run: python3 setup_tiktok.py
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from config import TIKTOK_SESSION_FILE

SESSION_FILE = Path(TIKTOK_SESSION_FILE)


def main():
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    print("Opening browser for TikTok login...")
    print("1. Log into TikTok in the browser window")
    print("2. Once you see the TikTok home feed, come back here and press Enter")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")

        input("\nPress Enter after you have logged in and can see the TikTok feed...")

        cookies = ctx.cookies()
        session_data = {"cookies": cookies}
        tmp = SESSION_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(session_data, indent=2))
        tmp.rename(SESSION_FILE)
        print(f"Session saved to {SESSION_FILE}")
        browser.close()


if __name__ == "__main__":
    main()
