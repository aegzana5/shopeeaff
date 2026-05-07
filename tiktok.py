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

            # Dismiss blocking modals via JS (overlay intercepts Playwright pointer events)
            page.evaluate("""
                const texts = ['Cancel', 'Not now', 'Skip', 'Got it'];
                document.querySelectorAll('button').forEach(btn => {
                    if (texts.includes(btn.textContent.trim())) btn.click();
                });
            """)
            time.sleep(1)

            # Upload file — direct input[type="file"] is faster than file chooser
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.first.set_input_files(str(video_path))
            else:
                # Fallback: trigger file chooser via upload button
                upload_btn = page.locator('[class*="upload"],[class*="Upload"]')
                if upload_btn.count() == 0:
                    raise RuntimeError("TikTok upload: no file input found on upload page")
                with page.expect_file_chooser(timeout=15000) as fc_info:
                    upload_btn.first.click()
                fc_info.value.set_files(str(video_path))
            time.sleep(5)

            # Fill caption via JS (modal overlay may still be fading out)
            full_caption = f"{caption}\n\n{HASHTAGS}"
            page.evaluate(f"""
                const el = document.querySelector('div[contenteditable="true"]')
                    || document.querySelector('textarea');
                if (el) {{
                    el.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, {json.dumps(full_caption)});
                }}
            """)
            time.sleep(1)

            # Post — use JS click to bypass any overlay
            page.evaluate("""
                const texts = ['Post', '投稿', 'โพสต์'];
                const buttons = Array.from(document.querySelectorAll('button'));
                const post = buttons.reverse().find(b => texts.includes(b.textContent.trim()));
                if (post) post.click();
            """)
            time.sleep(10)

            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            if str(e) == "SESSION_EXPIRED":
                raise RuntimeError("TikTok session expired. Run: python3 setup_tiktok.py") from None
            raise RuntimeError(f"TikTok post failed: {e}") from e
