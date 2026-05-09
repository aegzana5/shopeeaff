# Design: Instagram Caption Verify & Auto-Fix

**Date:** 2026-05-09  
**Status:** Approved

## Problem

Instagram posts are succeeding (returning "posted") but captions are sometimes empty. The caption field detection works inconsistently. This feature adds a post-posting verification step that checks the live post and edits the caption if missing, using the same Playwright browser session already open.

## Design

### `_verify_and_fix_caption(page, caption: str) -> bool`

New private function in `instagram.py`. Called at the end of both `_do_post()` and `post_reel_clip()` while the browser session is still open.

**Deterministic flow — explicit waits, no sleep-based timing:**

1. Navigate to profile: `page.goto(f"https://www.instagram.com/{IG_USERNAME}/")`
2. `page.wait_for_selector("article a[href*='/p/']", timeout=15000)` — wait for post grid
3. Click first post link (most recent = just posted)
4. `page.wait_for_selector('[role="dialog"]', timeout=10000)` — post overlay
5. Read caption: try `[role="dialog"] h1` then `[role="dialog"] span` — take first non-empty inner_text
6. If caption text present → log "Caption verified OK", return True
7. If caption empty:
   a. Click `[aria-label="More options"]` or `svg[aria-label*="more"]` (three-dot menu)
   b. `page.wait_for_selector('[role="menu"]', timeout=5000)`
   c. Click menu item whose text is "Edit" (exact)
   d. `page.wait_for_selector('[aria-label*="caption"], div[contenteditable="true"]', timeout=8000)`
   e. `lc.fill(caption)`
   f. Click "Done" button (`page.get_by_role("button", name="Done")`)
   g. `page.wait_for_selector('[role="dialog"]', timeout=5000)` — confirm dialog still open (save succeeded)
   h. Log "Caption missing — fixed via edit"
   i. Return True
8. Any exception → `log.warning(f"Caption verify failed: {e}")`, return False (non-fatal)

### Integration points

**`_do_post(page, image_path, caption)`** — add at end, after the Share success loop:
```python
_verify_and_fix_caption(page, caption)
```

**`post_reel_clip(...)`** — add after the Share success loop, before `ctx.storage_state(...)`:
```python
_verify_and_fix_caption(page, caption)
```

### Error handling

- Entire function in try/except — never raises, never blocks a successful post
- Each wait has an explicit timeout — no indefinite hangs
- Return value (bool) is logged but not acted on by callers

## What Does NOT Change

- Posting logic unchanged
- Session/cookie management unchanged
- No new dependencies

## Testing

Mock-based unit test: patch `page` with a mock that returns empty caption text, verify the edit flow (three-dot → Edit → fill → Done) is called. One test for "caption present" (no edit), one for "caption missing" (edit triggered).
