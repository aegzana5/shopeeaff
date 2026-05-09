"""
Instagram posting via Playwright (web interface).
Loads session from assets/ig_session.json (sessionid + csrftoken cookies).
When sessionid expires, user updates ig_session.json with fresh cookies from browser.
"""
import json
import logging
import time
from pathlib import Path

from config import IG_USERNAME

log = logging.getLogger(__name__)

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

    CAPTION_SELECTORS = [
        '[aria-label="Write a caption..."]',
        'textarea[aria-label*="caption"]',
        'div[aria-label*="caption"]',
        'div[role="textbox"]',
        'div[contenteditable="true"]',
    ]

    # Next through all steps until caption field appears (crop → filter → adjust → caption)
    for _ in range(5):
        if any(page.locator(s).count() > 0 for s in CAPTION_SELECTORS):
            break
        for txt in ["Next", "ถัดไป"]:
            lc = page.get_by_role("button", name=txt)
            if lc.count() > 0:
                lc.last.dispatch_event("click")
                time.sleep(2)
                break

    caption_filled = False
    for sel in CAPTION_SELECTORS:
        lc = page.locator(sel)
        if lc.count() > 0:
            lc.first.click()
            time.sleep(0.3)
            page.keyboard.type(caption, delay=30)
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

    _verify_and_fix_caption(page, caption)


def _verify_and_fix_caption(page, caption: str) -> bool:
    try:
        time.sleep(3)
        page.goto(
            f"https://www.instagram.com/{IG_USERNAME}/",
            wait_until="load",
            timeout=30000,
        )
        post_sel = "a[href*='/p/'], a[href*='/reel/']"
        page.wait_for_selector(post_sel, timeout=30000)
        page.evaluate("() => { document.querySelector(\"a[href*='/p/'], a[href*='/reel/']\")?.click() }")
        page.wait_for_selector('[role="dialog"]', timeout=15000)

        CAPTION_CONTAINER_SELS = [
            '[role="dialog"] div._a9zs',
            '[role="dialog"] ._a9zs',
            '[role="dialog"] article div[class*="caption"]',
        ]
        actual_caption = ""
        for sel in CAPTION_CONTAINER_SELS:
            el = page.locator(sel)
            if el.count() > 0:
                text = el.first.inner_text().strip()
                if text:
                    actual_caption = text
                    break

        if actual_caption:
            log.info("Caption verified OK")
            return True

        page.locator(
            '[aria-label="More options"], [aria-label="มีตัวเลือกเพิ่มเติม"]'
        ).first.click()
        page.wait_for_selector('[role="menu"]', timeout=5000)
        page.get_by_role("menuitem", name="Edit").click()

        edit_sel = (
            '[aria-label*="caption"], [aria-label*="คำบรรยาย"], div[contenteditable="true"]'
        )
        page.wait_for_selector(edit_sel, timeout=8000)
        edit_field = page.locator(edit_sel).first
        edit_field.click()
        time.sleep(0.3)
        page.keyboard.type(caption, delay=30)
        page.get_by_role("button", name="Done").click()
        time.sleep(2)
        log.info("Caption missing — fixed via edit")
        return True

    except Exception as e:
        log.warning(f"Caption verify/fix failed: {e}")
        return False


def _post_first_comment(page, hashtags: str) -> bool:
    """Post hashtags as first comment on most recent post. Non-fatal."""
    if not hashtags:
        return False
    try:
        time.sleep(2)
        page.goto(
            f"https://www.instagram.com/{IG_USERNAME}/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        post_sel = "a[href*='/p/'], a[href*='/reel/']"
        page.wait_for_selector(post_sel, timeout=15000)
        page.evaluate(
            "() => { document.querySelector(\"a[href*='/p/'], a[href*='/reel/']\")?.click() }"
        )
        page.wait_for_selector('[role="dialog"]', timeout=10000)

        comment_sel = (
            'textarea[aria-label*="comment"], '
            'textarea[placeholder*="comment"], '
            'textarea[aria-label*="ความคิดเห็น"]'
        )
        page.wait_for_selector(comment_sel, timeout=8000)
        comment_field = page.locator(comment_sel).first
        comment_field.click()
        page.keyboard.type(hashtags, delay=10)
        page.keyboard.press("Enter")
        time.sleep(2)
        log.info("First comment with hashtags posted")
        return True
    except Exception as e:
        log.warning(f"First comment failed: {e}")
        return False


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

            # Open create dialog → click "New post" then "Reel" from dropdown
            page.locator('[aria-label="New post"]').first.click()
            time.sleep(2)
            clicked = page.evaluate("""() => {
                const labels = ['Reel', 'รีล', 'ลีล'];
                const el = [...document.querySelectorAll('a, button, [role="menuitem"], span')]
                    .find(e => labels.includes(e.textContent.trim()) && e.tagName !== 'TITLE');
                if (el) { el.click(); return el.textContent.trim(); }
                return '';
            }""")
            if not clicked:
                log.warning("Reel dropdown option not found, falling back to Post")
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
            CAPTION_SELECTORS = [
                '[aria-label="Write a caption..."]',
                '[aria-label*="Write a caption"]',
                'textarea[aria-label*="caption"]',
                'div[aria-label*="caption"]',
                'div[aria-label*="คำบรรยาย"]',
                'div[role="textbox"]',
                'div[contenteditable="true"]',
                'textarea',
            ]

            def _find_caption_field(pg):
                for frame in [pg] + list(pg.frames):
                    for sel in CAPTION_SELECTORS:
                        try:
                            lc = frame.locator(sel)
                            if lc.count() > 0:
                                return frame, sel, lc.first
                        except Exception:
                            pass
                return None, None, None

            for _ in range(8):
                frm, sel, lc = _find_caption_field(page)
                if frm is not None:
                    break
                for txt in ["Next", "ถัดไป", "下一步", "Continue", "ต่อไป"]:
                    btn = page.get_by_role("button", name=txt)
                    if btn.count() > 0:
                        btn.last.dispatch_event("click")
                        time.sleep(3)
                        break
                else:
                    time.sleep(3)

            # Fill caption
            caption_filled = False
            frm, sel, lc = _find_caption_field(page)
            if lc is not None:
                lc.click()
                time.sleep(0.3)
                page.keyboard.type(caption, delay=30)
                time.sleep(1)
                log.info(f"Reel caption filled via selector: {sel}")
                caption_filled = True

            if not caption_filled:
                # JS fallback — React contenteditable via native input value setter
                filled = page.evaluate("""(cap) => {
                    const candidates = [...document.querySelectorAll('[contenteditable="true"], textarea, [role="textbox"]')];
                    const el = candidates.find(e => e.offsetParent !== null) || candidates[0];
                    if (!el) return '';
                    el.focus();
                    const setter = Object.getOwnPropertyDescriptor(
                        el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLElement.prototype,
                        el.tagName === 'TEXTAREA' ? 'value' : 'textContent'
                    );
                    if (setter && setter.set) setter.set.call(el, cap);
                    else el.textContent = cap;
                    el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: cap}));
                    return el.getAttribute('aria-label') || el.tagName;
                }""", caption)
                if filled:
                    log.info(f"Reel caption filled via JS fallback (el={filled})")
                    caption_filled = True

            if not caption_filled:
                diag = page.evaluate("() => { const d = document.querySelector('[role=\"dialog\"]'); return d ? d.innerText.slice(0, 300) : document.body.innerText.slice(0, 300); }")
                log.warning(f"Reel caption field not found — post will have no caption. Page text: {diag!r}")

            # Share
            page.evaluate("() => { [...document.querySelectorAll('[role=\"dialog\"] [role=\"button\"]')].find(b => b.innerText.trim() === 'Share')?.click() }")
            for _ in range(15):
                time.sleep(2)
                dlg = page.evaluate("() => { let d = document.querySelector('[role=\"dialog\"]'); return d ? d.innerText : ''; }")
                if "Post shared" in dlg or "Your post" in dlg:
                    break

            _verify_and_fix_caption(page, caption)

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
