"""
TikTok clip upload via Playwright.
Session loaded from assets/tiktok_session.json.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from config import TIKTOK_SESSION_FILE

SESSION_FILE = Path(TIKTOK_SESSION_FILE)

HASHTAGS = "#ShopeeThailand #แฟชั่น #ของดีราคาถูก #OOTDThailand #ShopeeTH"


def _load_cookies():
    if not SESSION_FILE.exists():
        raise RuntimeError(
            "No TikTok session found. Run: python3 setup_tiktok.py"
        )
    data = json.loads(SESSION_FILE.read_text())
    cookies = data.get("cookies", [])
    for c in cookies:
        c["secure"] = bool(c.get("secure", False))
        c["httpOnly"] = bool(c.get("httpOnly", False))
    return cookies


def post_clip(video_path: Path, caption: str) -> str:
    """Upload clip to TikTok. Returns 'posted' on success."""
    video_path = Path(video_path).absolute()
    cookies = _load_cookies()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        try:
            page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            if "login" in page.url:
                raise RuntimeError("SESSION_EXPIRED")

            # Upload file — direct input[type="file"]
            file_input = page.locator('input[type="file"]')
            if file_input.count() == 0:
                raise RuntimeError("TikTok upload: no file input found on upload page")
            file_input.first.set_input_files(str(video_path))
            time.sleep(5)

            # Dismiss blocking modal (e.g. "Turn on content checks?") — click Cancel
            dialog = page.locator('[role="dialog"]')
            if dialog.count() > 0:
                cancel = dialog.locator('button').first
                cancel.dispatch_event("click")
                time.sleep(1)

            # Fill caption — dispatch_event click to focus, then type
            caption_el = page.locator('div[contenteditable="true"]').first
            caption_el.dispatch_event("click")
            time.sleep(0.3)
            page.keyboard.type(f"{caption}\n\n{HASHTAGS}")
            time.sleep(1)

            # Set privacy to Everyone/Public before posting
            for privacy_txt in ["Everyone", "ทุกคน", "公开"]:
                lc = page.locator(f'button:has-text("{privacy_txt}")')
                if lc.count() > 0:
                    lc.first.dispatch_event("click")
                    time.sleep(0.5)
                    break

            # Post — dispatch_event bypasses overlay pointer-events check
            for txt in ["Post", "投稿", "โพสต์"]:
                lc = page.locator(f'button:has-text("{txt}")')
                if lc.count() > 0:
                    lc.last.scroll_into_view_if_needed()
                    lc.last.dispatch_event("click")
                    break
            time.sleep(12)

            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            if str(e) == "SESSION_EXPIRED":
                raise RuntimeError("TikTok session expired. Run: python3 setup_tiktok.py") from None
            raise RuntimeError(f"TikTok post failed: {e}") from e
