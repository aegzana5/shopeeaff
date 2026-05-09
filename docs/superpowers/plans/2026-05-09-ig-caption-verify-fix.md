# Instagram Caption Verify & Auto-Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every Instagram post, navigate to the profile, check the most recent post's caption, and auto-edit it if missing — using the same Playwright session already open.

**Architecture:** Add `_verify_and_fix_caption(page, caption)` to `instagram.py`. Call it from both `_do_post()` and `post_reel_clip()` after the Share success loop. Function is non-fatal: any failure logs a warning and returns False, never blocking a successful post.

**Tech Stack:** Playwright (already in use), pytest, unittest.mock

---

## Task 1: Write failing tests for `_verify_and_fix_caption`

**Files:**
- Create: `tests/test_instagram.py`

- [ ] **Step 1: Create `tests/test_instagram.py` with two failing tests**

```python
"""Tests for instagram._verify_and_fix_caption."""
from unittest.mock import MagicMock, patch
import pytest


def _make_page(caption_text: str):
    """Build a mock Playwright page. caption_text='' simulates missing caption."""
    page = MagicMock()

    # Caption locator — used inside [role="dialog"] h1 and span checks
    caption_locator = MagicMock()
    if caption_text:
        caption_locator.count.return_value = 1
        caption_locator.first.inner_text.return_value = caption_text
    else:
        caption_locator.count.return_value = 0

    # Edit field locator — used after clicking Edit
    edit_locator = MagicMock()
    edit_locator.first = MagicMock()

    def locator_side_effect(sel):
        if "h1" in sel or "span" in sel:
            return caption_locator
        return edit_locator

    page.locator.side_effect = locator_side_effect
    return page, edit_locator


def test_verify_caption_already_present_returns_true():
    """When caption exists on post, return True without triggering edit."""
    from instagram import _verify_and_fix_caption

    page, edit_locator = _make_page("Existing caption text")

    with patch("instagram.IG_USERNAME", "testuser"):
        result = _verify_and_fix_caption(page, "Existing caption text")

    assert result is True
    # No edit flow: get_by_role("menuitem") should never be called
    for call_args in page.get_by_role.call_args_list:
        assert call_args[0][0] != "menuitem", "Edit menuitem should not be clicked when caption is present"


def test_verify_caption_missing_triggers_edit_and_returns_true():
    """When caption is empty, trigger edit flow and fill caption."""
    from instagram import _verify_and_fix_caption

    page, edit_locator = _make_page("")  # no caption

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time") as mock_time:
        mock_time.sleep = MagicMock()
        result = _verify_and_fix_caption(page, "My product caption")

    assert result is True
    # Edit menu item was clicked
    page.get_by_role.assert_any_call("menuitem", name="Edit")
    # Caption field was filled
    edit_locator.first.fill.assert_called_once_with("My product caption")
    # Done button was clicked
    page.get_by_role.assert_any_call("button", name="Done")


def test_verify_caption_exception_returns_false():
    """Any Playwright exception returns False (non-fatal)."""
    from instagram import _verify_and_fix_caption

    page = MagicMock()
    page.goto.side_effect = Exception("network error")

    with patch("instagram.IG_USERNAME", "testuser"):
        result = _verify_and_fix_caption(page, "caption")

    assert result is False
```

- [ ] **Step 2: Run tests to confirm they fail (function not yet defined)**

```bash
/Users/aegisen/fashion-bot/.venv/bin/python3 -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: `ImportError` or `AttributeError: module 'instagram' has no attribute '_verify_and_fix_caption'`

---

## Task 2: Implement `_verify_and_fix_caption`

**Files:**
- Modify: `instagram.py` — add function before `post_reel` definition

- [ ] **Step 1: Add `_verify_and_fix_caption` to `instagram.py`**

Insert this function directly before `def post_reel(` in `instagram.py`:

```python
def _verify_and_fix_caption(page, caption: str) -> bool:
    """Navigate to profile, check most recent post caption, edit if missing.

    Non-fatal: any failure logs a warning and returns False.
    """
    try:
        page.goto(
            f"https://www.instagram.com/{IG_USERNAME}/",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        page.wait_for_selector("article a[href*='/p/']", timeout=15000)
        page.locator("article a[href*='/p/']").first.click()
        page.wait_for_selector('[role="dialog"]', timeout=10000)

        # Read caption from post overlay
        actual_caption = ""
        for sel in ['[role="dialog"] h1', '[role="dialog"] span']:
            el = page.locator(sel)
            if el.count() > 0:
                text = el.first.inner_text().strip()
                if text:
                    actual_caption = text
                    break

        if actual_caption:
            log.info("Caption verified OK")
            return True

        # Caption missing — open edit flow
        page.locator(
            '[aria-label="More options"], [aria-label="มีตัวเลือกเพิ่มเติม"]'
        ).first.click()
        page.wait_for_selector('[role="menu"]', timeout=5000)
        page.get_by_role("menuitem", name="Edit").click()

        edit_sel = (
            '[aria-label*="caption"], [aria-label*="คำบรรยาย"], div[contenteditable="true"]'
        )
        page.wait_for_selector(edit_sel, timeout=8000)
        page.locator(edit_sel).first.fill(caption)
        page.get_by_role("button", name="Done").click()
        time.sleep(2)
        log.info("Caption missing — fixed via edit")
        return True

    except Exception as e:
        log.warning(f"Caption verify/fix failed: {e}")
        return False
```

- [ ] **Step 2: Run tests**

```bash
/Users/aegisen/fashion-bot/.venv/bin/python3 -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: `3 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_instagram.py instagram.py
git commit -m "feat(instagram): add _verify_and_fix_caption with tests"
```

---

## Task 3: Integrate into `_do_post`

**Files:**
- Modify: `instagram.py` — `_do_post()` function

- [ ] **Step 1: Add call to `_verify_and_fix_caption` at end of `_do_post`**

In `_do_post(page, image_path, caption)`, find the Share success loop:

```python
    page.evaluate("() => { [...document.querySelectorAll('[role=\"dialog\"] [role=\"button\"]')].find(b => b.innerText.trim() === 'Share')?.click() }")
    for _ in range(15):
        time.sleep(2)
        dlg = page.evaluate("() => { let d = document.querySelector('[role=\"dialog\"]'); return d ? d.innerText : ''; }")
        if "Post shared" in dlg or "Your post" in dlg:
            break
```

Immediately after that block (end of `_do_post`), add:

```python
    _verify_and_fix_caption(page, caption)
```

- [ ] **Step 2: Run full test suite**

```bash
/Users/aegisen/fashion-bot/.venv/bin/python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `60 passed` (57 existing + 3 new instagram tests)

- [ ] **Step 3: Commit**

```bash
git add instagram.py
git commit -m "feat(instagram): verify+fix caption after image post"
```

---

## Task 4: Integrate into `post_reel_clip` and push

**Files:**
- Modify: `instagram.py` — `post_reel_clip()` function

- [ ] **Step 1: Add call to `_verify_and_fix_caption` in `post_reel_clip`**

In `post_reel_clip`, find the Share success loop and the line `ctx.storage_state(path=str(STATE_FILE))`. Insert the verify call between the Share loop and `ctx.storage_state`:

```python
            # Share success loop is above this line
            _verify_and_fix_caption(page, caption)

            ctx.storage_state(path=str(STATE_FILE))
            browser.close()
            return "posted"
```

- [ ] **Step 2: Run full test suite**

```bash
/Users/aegisen/fashion-bot/.venv/bin/python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `60 passed`

- [ ] **Step 3: Commit and push**

```bash
git add instagram.py
git commit -m "feat(instagram): verify+fix caption after reel post"
git push
```
