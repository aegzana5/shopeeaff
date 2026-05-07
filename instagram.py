"""
Instagram posting via Playwright (web interface).
Loads session from assets/ig_session.json (sessionid + csrftoken cookies).
When sessionid expires, user updates ig_session.json with fresh cookies from browser.
"""
import json
import time
from pathlib import Path

from config import IG_USERNAME

SESSION_FILE = Path("assets/ig_session.json")
STATE_FILE = Path("assets/browser_state.json")


def _build_browser_state():
    """Build Playwright browser_state.json from ig_session.json cookies."""
    if not SESSION_FILE.exists():
        raise RuntimeError("assets/ig_session.json not found — add sessionid cookie first")

    saved = json.loads(SESSION_FILE.read_text())
    cookies = saved.get("cookies", {})
    sessionid = cookies.get("sessionid")
    csrftoken = cookies.get("csrftoken")
    ds_user_id = cookies.get("ds_user_id")

    if not sessionid:
        raise RuntimeError("No sessionid in assets/ig_session.json")

    playwright_cookies = [
        {
            "name": "sessionid",
            "value": sessionid,
            "domain": ".instagram.com",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        },
    ]
    if csrftoken:
        playwright_cookies.append({
            "name": "csrftoken",
            "value": csrftoken,
            "domain": ".instagram.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        })
    if ds_user_id:
        playwright_cookies.append({
            "name": "ds_user_id",
            "value": ds_user_id,
            "domain": ".instagram.com",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        })

    state = {"cookies": playwright_cookies, "origins": []}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def _make_context(p):
    if not STATE_FILE.exists():
        _build_browser_state()

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
        locale="en-US",
        storage_state=str(STATE_FILE),
    )
    return browser, ctx


def _ensure_logged_in(page) -> bool:
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    if "/accounts/login" in page.url or page.locator('[name="email"]').count() > 0:
        return False
    return True


def post_image(image_path: Path, caption: str) -> str:
    """Post single image via Playwright web interface. Returns 'posted'."""
    from playwright.sync_api import sync_playwright

    image_path = Path(image_path).absolute()

    with sync_playwright() as p:
        browser, ctx = _make_context(p)
        page = ctx.new_page()

        if not _ensure_logged_in(page):
            browser.close()
            # Session expired — rebuild state and retry once
            STATE_FILE.unlink(missing_ok=True)
            raise RuntimeError(
                "Instagram session expired. Update sessionid in assets/ig_session.json"
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
    if "instagram.com" not in page.url:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

    for sel in [
        '[aria-label="New post"]',
        'svg[aria-label="New post"]',
        '[data-testid="new-post-button"]',
    ]:
        if page.locator(sel).count() > 0:
            page.locator(sel).first.click()
            break
    else:
        page.click('a[href="/create/style/"]', timeout=5000)
    time.sleep(1)

    for txt in ["Post", "post"]:
        lc = page.locator(f'text="{txt}"')
        if lc.count() > 0:
            lc.first.click()
            time.sleep(1)
            break

    with page.expect_file_chooser(timeout=10000) as fc_info:
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

    page.locator('text="Next"').last.click()
    time.sleep(2)

    next_lc = page.locator('text="Next"')
    if next_lc.count() > 0:
        next_lc.last.click()
        time.sleep(2)

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

    page.locator('text="Share"').last.click()
    time.sleep(8)


def post_reel(video_path: Path, caption: str) -> str:
    raise NotImplementedError("Reel posting via Playwright not yet implemented")


def post_reel_clip(video_path: Path, caption: str) -> str:
    """Cross-post a video clip to Instagram Reels via Playwright web interface. Returns 'posted'."""
    from playwright.sync_api import sync_playwright

    video_path = Path(video_path).absolute()

    with sync_playwright() as p:
        browser, ctx = _make_context(p)
        page = ctx.new_page()

        if not _ensure_logged_in(page):
            browser.close()
            raise RuntimeError(
                "Instagram session expired. Update sessionid in assets/ig_session.json"
            )

        try:
            if "instagram.com" not in page.url:
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

            # Click "New post" button
            for sel in [
                '[aria-label="New post"]',
                'svg[aria-label="New post"]',
                '[data-testid="new-post-button"]',
            ]:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    break
            else:
                page.click('a[href="/create/style/"]', timeout=5000)
            time.sleep(1)

            # Click "Reel" option
            for sel in ['text="Reel"', '[aria-label="Reel"]']:
                lc = page.locator(sel)
                if lc.count() > 0:
                    lc.first.click()
                    time.sleep(1)
                    break

            # Upload video via file chooser
            with page.expect_file_chooser(timeout=15000) as fc_info:
                for sel in ['text="Select from computer"', 'text="Select From Computer"', '[type="file"]']:
                    lc = page.locator(sel)
                    if lc.count() > 0:
                        lc.first.click()
                        break
            fc_info.value.set_files(str(video_path))
            time.sleep(8)

            # Click Next (may appear multiple times)
            page.locator('text="Next"').last.click()
            time.sleep(2)

            next_lc = page.locator('text="Next"')
            if next_lc.count() > 0:
                next_lc.last.click()
                time.sleep(2)

            # Fill caption
            for sel in [
                '[aria-label="Write a caption..."]',
                'div[contenteditable="true"]',
            ]:
                lc = page.locator(sel)
                if lc.count() > 0:
                    lc.first.click()
                    lc.first.fill(caption)
                    break
            time.sleep(1)

            # Share
            page.locator('text="Share"').last.click()
            time.sleep(10)

            ctx.storage_state(path=str(STATE_FILE))
            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Reel post failed: {e}") from e


class _FakeClient:
    username = IG_USERNAME

def get_client():
    return _FakeClient()
