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
    return data.get("cookies", [])


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
            time.sleep(3)

            if "login" in page.url:
                raise RuntimeError("SESSION_EXPIRED")

            # Upload file
            upload_sel = None
            for sel in ['input[type="file"]', '[class*="upload"]']:
                if page.locator(sel).count() > 0:
                    upload_sel = sel
                    break
            if upload_sel is None:
                raise RuntimeError("TikTok upload: no file input found on upload page")

            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.locator(upload_sel).first.click()
            fc_info.value.set_files(str(video_path))
            time.sleep(5)

            # Fill caption
            full_caption = f"{caption}\n\n{HASHTAGS}"
            for sel in ['div[contenteditable="true"]', 'textarea']:
                lc = page.locator(sel)
                if lc.count() > 0:
                    lc.first.click()
                    page.keyboard.type(full_caption)
                    break
            time.sleep(1)

            # Post
            for txt in ["Post", "投稿", "โพสต์"]:
                lc = page.locator(f'button:has-text("{txt}")')
                if lc.count() > 0:
                    lc.last.click()
                    break
            time.sleep(10)

            return "posted"
        except Exception as e:
            browser.close()
            if str(e) == "SESSION_EXPIRED":
                raise RuntimeError("TikTok session expired. Run: python3 setup_tiktok.py") from None
            raise RuntimeError(f"TikTok post failed: {e}") from e
