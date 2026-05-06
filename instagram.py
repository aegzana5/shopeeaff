"""
Instagram posting via Playwright (real browser — handles web sessions natively).
Browser state persisted to disk so re-login is rare.
"""
import time
from pathlib import Path
from urllib.parse import unquote

from config import IG_USERNAME, IG_PASSWORD

STATE_FILE = Path("assets/browser_state.json")

IG_COOKIES = [
    {"name": "sessionid",   "value": unquote("25336031048%3AODklGG3P78hmeS%3A27%3AAYgOu4ViVuBORTQMjgwG1sstHd0yaXrAgfaIEDLwaQ"),
     "domain": ".instagram.com", "path": "/"},
    {"name": "csrftoken",   "value": "56c1LXqpMP8xQG3gmtcGbIPaV7mjw8AI",
     "domain": ".instagram.com", "path": "/"},
    {"name": "ds_user_id",  "value": "25336031048",
     "domain": ".instagram.com", "path": "/"},
]


def _make_context(p, inject_cookies: bool = False):
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    kwargs = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "locale": "en-US",
    }
    if STATE_FILE.exists() and not inject_cookies:
        kwargs["storage_state"] = str(STATE_FILE)
    ctx = browser.new_context(**kwargs)
    if inject_cookies:
        ctx.add_cookies(IG_COOKIES)
    return browser, ctx


def _ensure_logged_in(page) -> bool:
    """Return True if logged in. Raises if not (run setup_instagram.py first)."""
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    if "/accounts/login" in page.url or page.locator('[name="email"]').count() > 0:
        return False
    return True


def post_image(image_path: Path, caption: str) -> str:
    """Post single image via Playwright web interface. Returns 'posted'."""
    from playwright.sync_api import sync_playwright

    image_path = Path(image_path).absolute()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        raise RuntimeError(
            "No browser session found. Run: python3 setup_instagram.py"
        )

    with sync_playwright() as p:
        browser, ctx = _make_context(p, inject_cookies=False)
        page = ctx.new_page()

        ok = _ensure_logged_in(page)
        if not ok:
            browser.close()
            raise RuntimeError(
                "Instagram session expired. Run: python3 setup_instagram.py"
            )

        try:
            _do_post(page, image_path, caption)
            ctx.storage_state(path=str(STATE_FILE))
            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Post failed: {e}") from e


def _do_post(page, image_path: Path, caption: str):
    """Interact with Instagram web UI to create a post."""
    # Navigate to home to be safe
    if "instagram.com" not in page.url:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

    # Click "Create" / New Post button
    # Try several known selectors
    for sel in [
        '[aria-label="New post"]',
        'svg[aria-label="New post"]',
        '[data-testid="new-post-button"]',
    ]:
        if page.locator(sel).count() > 0:
            page.locator(sel).first.click()
            break
    else:
        # Fallback: look for "+" icon in nav via SVG title
        page.click('a[href="/create/style/"]', timeout=5000)
    time.sleep(1)

    # Click "Post" in the dropdown/menu if it appears
    for txt in ["Post", "post"]:
        lc = page.locator(f'text="{txt}"')
        if lc.count() > 0:
            lc.first.click()
            time.sleep(1)
            break

    # Upload file via file chooser
    with page.expect_file_chooser(timeout=10000) as fc_info:
        # Try "Select from computer" button
        for sel in [
            'text="Select from computer"',
            'text="Select From Computer"',
            '[type="file"]',
        ]:
            lc = page.locator(sel)
            if lc.count() > 0:
                lc.first.click()
                break
    fc_info.value.set_files(str(image_path))
    time.sleep(3)

    # Click Next through crop step
    page.locator('button:has-text("Next")').last.click()
    time.sleep(2)

    # Click Next through filter/effects step
    next_btns = page.locator('button:has-text("Next")')
    if next_btns.count() > 0:
        next_btns.last.click()
        time.sleep(2)

    # Fill caption
    for sel in [
        '[aria-label="Write a caption..."]',
        'textarea[placeholder*="caption"]',
        'div[contenteditable="true"]',
    ]:
        lc = page.locator(sel)
        if lc.count() > 0:
            lc.first.click()
            lc.first.fill(caption)
            break
    time.sleep(1)

    # Share
    page.locator('button:has-text("Share")').last.click()
    time.sleep(8)  # Wait for post to complete


def post_reel(video_path: Path, caption: str) -> str:
    """Post reel via Playwright. Returns 'posted'."""
    raise NotImplementedError("Reel posting via Playwright not yet implemented")


# Backward-compat stub for test scripts
class _FakeClient:
    username = IG_USERNAME

def get_client():
    return _FakeClient()
