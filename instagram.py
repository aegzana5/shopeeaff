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

    # Open create dropdown → click Post
    page.locator('[aria-label="New post"]').first.click()
    time.sleep(2)
    page.get_by_text("Post", exact=True).first.click()
    time.sleep(3)

    # Inject file directly — search page and all frames
    file_input = None
    for attempt in range(10):
        for frame in [page] + list(page.frames):
            fi = frame.locator('input[type="file"]')
            if fi.count() > 0:
                file_input = fi.first
                break
        if file_input:
            break
        time.sleep(1)
    if file_input is None:
        raise RuntimeError("Instagram: no file input found")
    file_input.set_input_files(str(image_path))
    time.sleep(3)

    # Next through all steps until caption field appears (crop → filter → adjust → caption)
    for _ in range(4):
        for sel in ['[aria-label="Write a caption..."]', 'textarea[aria-label*="caption"]']:
            if page.locator(sel).count() > 0:
                break
        else:
            for txt in ["Next", "ถัดไป"]:
                lc = page.get_by_role("button", name=txt)
                if lc.count() > 0:
                    lc.last.dispatch_event("click")
                    time.sleep(2)
                    break
            continue
        break

    caption_selectors = [
        '[aria-label="Write a caption..."]',
        'textarea[aria-label*="caption"]',
        'div[aria-label*="caption"]',
        'div[contenteditable="true"]',
    ]
    caption_filled = False
    for sel in caption_selectors:
        lc = page.locator(sel)
        if lc.count() > 0:
            lc.first.click()
            time.sleep(0.5)
            page.keyboard.type(caption, delay=20)
            time.sleep(1)
            log.info(f"Caption filled via selector: {sel}")
            caption_filled = True
            break
    if not caption_filled:
        log.warning("Caption field not found — post will have no caption")

    page.evaluate("() => { [...document.querySelectorAll('[role=\"dialog\"] [role=\"button\"]')].find(b => b.innerText.trim() === 'Share')?.click() }")
    for _ in range(15):
        time.sleep(2)
        dlg = page.evaluate("() => { let d = document.querySelector('[role=\"dialog\"]'); return d ? d.innerText : ''; }")
        if "Post shared" in dlg or "Your post" in dlg:
            break


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
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Open create dialog → click "New post" then "Post" from dropdown
            page.locator('[aria-label="New post"]').first.click()
            time.sleep(2)
            page.get_by_text("Post", exact=True).first.click()
            time.sleep(3)

            # Find file input — may appear in page or iframe
            file_input = None
            for attempt in range(10):
                for frame in [page] + list(page.frames):
                    fi = frame.locator('input[type="file"]')
                    if fi.count() > 0:
                        file_input = fi.first
                        break
                if file_input:
                    break
                time.sleep(1)
            if file_input is None:
                raise RuntimeError("Instagram: no file input found after dialog open")
            file_input.set_input_files(str(video_path))
            time.sleep(8)

            # Click through Next steps until caption field appears
            for _ in range(5):
                for sel in ['[aria-label="Write a caption..."]', 'textarea[aria-label*="caption"]']:
                    if page.locator(sel).count() > 0:
                        break
                else:
                    for txt in ["Next", "ถัดไป", "下一步"]:
                        lc = page.get_by_role("button", name=txt)
                        if lc.count() > 0:
                            lc.last.dispatch_event("click")
                            time.sleep(2)
                            break
                    continue
                break

            # Fill caption
            caption_selectors = [
                '[aria-label="Write a caption..."]',
                'textarea[aria-label*="caption"]',
                'div[aria-label*="caption"]',
                'div[contenteditable="true"]',
            ]
            caption_filled = False
            for sel in caption_selectors:
                lc = page.locator(sel)
                if lc.count() > 0:
                    lc.first.click()
                    time.sleep(0.5)
                    page.keyboard.type(caption, delay=20)
                    time.sleep(1)
                    log.info(f"Reel caption filled via selector: {sel}")
                    caption_filled = True
                    break
            if not caption_filled:
                log.warning("Reel caption field not found — post will have no caption")

            # Share
            page.evaluate("() => { [...document.querySelectorAll('[role=\"dialog\"] [role=\"button\"]')].find(b => b.innerText.trim() === 'Share')?.click() }")
            for _ in range(15):
                time.sleep(2)
                dlg = page.evaluate("() => { let d = document.querySelector('[role=\"dialog\"]'); return d ? d.innerText : ''; }")
                if "Post shared" in dlg or "Your post" in dlg:
                    break

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
