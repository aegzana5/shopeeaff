"""
TikTok clip upload via Playwright.
Session loaded from assets/tiktok_session.json.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from config import TIKTOK_SESSION_FILE, TIKTOK_ENABLED

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
    if not TIKTOK_ENABLED:
        raise RuntimeError("TikTok posting disabled (TIKTOK_ENABLED=false)")
    video_path = Path(video_path).absolute()
    cookies = _load_cookies()

    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        try:
            page.goto("https://www.tiktok.com/upload", wait_until="networkidle", timeout=45000)
            time.sleep(5)

            if "login" in page.url:
                raise RuntimeError("SESSION_EXPIRED")

            # TikTok embeds the uploader in an iframe — search all frames
            file_input = None
            for frame in page.frames:
                fi = frame.locator('input[type="file"]')
                if fi.count() > 0:
                    file_input = fi.first
                    break
            if file_input is None:
                raise RuntimeError("TikTok upload: no file input found on upload page")
            file_input.set_input_files(str(video_path))
            time.sleep(5)

            # Determine which frame hosts the uploader UI (same frame as file input)
            upload_frame = page
            for frame in page.frames:
                if frame.locator('div[contenteditable="true"]').count() > 0:
                    upload_frame = frame
                    break

            # Dismiss blocking modal (e.g. "Turn on content checks?") — click Cancel
            dialog = upload_frame.locator('[role="dialog"]')
            if dialog.count() > 0:
                cancel = dialog.locator('button').first
                cancel.dispatch_event("click")
                time.sleep(1)

            # Fill caption — dispatch_event click to focus, then type
            caption_el = upload_frame.locator('div[contenteditable="true"]').first
            caption_el.dispatch_event("click")
            time.sleep(0.3)
            upload_frame.evaluate(f'document.execCommand("insertText", false, {json.dumps(caption + chr(10) + chr(10) + HASHTAGS)})')
            time.sleep(1)

            # Set privacy to Everyone/Public before posting
            for privacy_txt in ["Everyone", "ทุกคน", "公开"]:
                lc = upload_frame.locator(f'button:has-text("{privacy_txt}")')
                if lc.count() > 0:
                    lc.first.dispatch_event("click")
                    time.sleep(0.5)
                    break

            # Post — dispatch_event bypasses overlay pointer-events check
            for txt in ["Post", "投稿", "โพสต์"]:
                lc = upload_frame.locator(f'button:has-text("{txt}")')
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


def update_bio(link: str) -> bool:
    """Update TikTok profile bio with affiliate link. Returns True on success."""
    if not TIKTOK_ENABLED:
        return False
    cookies = _load_cookies()
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        try:
            page.goto("https://www.tiktok.com/setting", wait_until="networkidle", timeout=30000)
            if "login" in page.url:
                browser.close()
                return False
            # Navigate to profile edit
            page.goto("https://www.tiktok.com/@me/edit", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            # Find bio textarea
            bio_field = page.locator('textarea[name="bio"], textarea[placeholder*="bio" i], div[data-e2e="bio-input"]').first
            if bio_field.count() == 0:
                # Try generic textarea
                bio_field = page.locator("textarea").first
            if bio_field.count() == 0:
                browser.close()
                return False
            bio_field.triple_click()
            bio_field.fill(link)
            time.sleep(1)
            # Save
            for save_txt in ["Save", "บันทึก", "保存"]:
                btn = page.locator(f'button:has-text("{save_txt}")')
                if btn.count() > 0:
                    btn.first.click()
                    break
            time.sleep(2)
            browser.close()
            return True
        except Exception as e:
            browser.close()
            return False
