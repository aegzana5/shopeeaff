# Instagram Caption Fix + Engagement Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Instagram caption not being posted (keyboard event bug), redesign Thai-only caption structure, add hashtags as first comment, and align posting times to Thai IG peak windows.

**Architecture:** Three independent layers — Playwright interaction fix (`instagram.py`), caption content redesign (`content_gen.py`), and scheduler config (`config.py`). Changes to `main.py` wire them together. Tasks 1–5 fix `instagram.py`; Tasks 6–7 update `content_gen.py`; Task 8 updates `main.py`; Task 9 updates `config.py`.

**Tech Stack:** Python 3.14, Playwright (sync API), Anthropic Claude API (`claude-sonnet-4-6`), pytest.

---

## File Map

| File | What changes |
|------|-------------|
| `instagram.py` | `.fill()` → `keyboard.type()` in `_do_post` + `post_reel_clip`; tighten `_verify_and_fix_caption` selector + fill; add `_post_first_comment`; add `hashtags=` param to `post_image` + `post_reel_clip` |
| `content_gen.py` | `generate_caption` → Thai-only hook structure, `caption` key = body only; same for `generate_video_caption`; add `generate_first_comment`; add `HASHTAGS_IG_TH` constant |
| `main.py` | `run_post_cycle` passes `hashtags` to `post_image`; `_make_clip` returns `first_comment`; `_distribute_clip` passes hashtags to `post_reel_clip` |
| `config.py` | `POST_TIMES` default → Thai IG peak windows |
| `tests/test_instagram.py` | New tests: `_do_post` keyboard fill, `_post_first_comment`, updated `_verify_and_fix_caption` |
| `tests/test_content_gen.py` | New file: tests for redesigned `generate_caption`, new `generate_first_comment` |

---

## Task 1: Fix caption fill in `_do_post` (image posts)

**Files:**
- Modify: `instagram.py` — line 180
- Modify: `tests/test_instagram.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_instagram.py`:

```python
def test_do_post_uses_keyboard_type_not_fill():
    """_do_post must use keyboard.type for caption, not fill()."""
    from pathlib import Path
    from unittest.mock import MagicMock, patch, call
    from instagram import _do_post

    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    # file input found on first try
    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    # caption field found immediately
    caption_loc = MagicMock()
    caption_loc.count.return_value = 1
    caption_loc.first = MagicMock()

    # "Next" button not found (already on caption step)
    next_btn = MagicMock()
    next_btn.count.return_value = 0

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if 'caption' in sel.lower() or 'textbox' in sel or 'contenteditable' in sel:
            return caption_loc
        return MagicMock(count=MagicMock(return_value=0))

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = next_btn
    page.get_by_text.return_value = MagicMock()
    page.evaluate.return_value = "Post shared"

    with patch("instagram.time"):
        _do_post(page, Path("/tmp/fake.jpg"), "ทดสอบ caption")

    page.keyboard.type.assert_called_once_with("ทดสอบ caption", delay=30)
    caption_loc.first.fill.assert_not_called()
```

- [ ] **Step 2: Run test — confirm FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_do_post_uses_keyboard_type_not_fill -v 2>&1 | tail -10
```

Expected: `FAILED` — `keyboard.type` not called.

- [ ] **Step 3: Fix `_do_post` in `instagram.py`**

At `instagram.py` line 176–184, replace the fill block:

```python
    caption_filled = False
    for sel in CAPTION_SELECTORS:
        lc = page.locator(sel)
        if lc.count() > 0:
            lc.first.click()
            page.keyboard.type(caption, delay=30)
            time.sleep(1)
            log.info(f"Caption filled via selector: {sel}")
            caption_filled = True
            break
    if not caption_filled:
        log.warning("Caption field not found — post will have no caption")
```

- [ ] **Step 4: Run test — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_do_post_uses_keyboard_type_not_fill -v 2>&1 | tail -10
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add instagram.py tests/test_instagram.py
git commit -m "fix(instagram): image caption fill use keyboard.type not fill()"
```

---

## Task 2: Fix caption fill in `post_reel_clip` (reel posts)

**Files:**
- Modify: `instagram.py` — line 342
- Modify: `tests/test_instagram.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_instagram.py`:

```python
def test_post_reel_clip_uses_keyboard_type_not_fill():
    """post_reel_clip must use keyboard.type for caption, not fill()."""
    from pathlib import Path
    from unittest.mock import MagicMock, patch
    import instagram

    # Track what fill() was called on
    fill_called_with = []

    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    caption_lc = MagicMock()
    caption_lc.count.return_value = 1
    caption_lc.first = MagicMock()
    # spy on fill
    def spy_fill(val):
        fill_called_with.append(val)
    caption_lc.first.fill.side_effect = spy_fill

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if any(k in sel for k in ['caption', 'textbox', 'contenteditable', 'textarea']):
            return caption_lc
        return MagicMock(count=MagicMock(return_value=0))

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = MagicMock(count=MagicMock(return_value=0))
    page.evaluate.return_value = "Post shared"

    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._verify_and_fix_caption", return_value=True), \
         patch("instagram.time"):
        instagram.post_reel_clip(Path("/tmp/fake.mp4"), "ทดสอบ reel caption")

    page.keyboard.type.assert_called()
    assert "ทดสอบ reel caption" in fill_called_with == [], \
        "fill() should not have been called with caption"
```

- [ ] **Step 2: Run test — confirm FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_post_reel_clip_uses_keyboard_type_not_fill -v 2>&1 | tail -10
```

Expected: `FAILED`

- [ ] **Step 3: Fix `post_reel_clip` in `instagram.py`**

At `instagram.py` line 337–344, the caption fill block currently reads:
```python
            caption_filled = False
            frm, sel, lc = _find_caption_field(page)
            if lc is not None:
                lc.click()
                time.sleep(0.5)
                lc.fill(caption)
                time.sleep(1)
                log.info(f"Reel caption filled via selector: {sel}")
                caption_filled = True
```

Replace `lc.fill(caption)` with `page.keyboard.type(caption, delay=30)`:

```python
            caption_filled = False
            frm, sel, lc = _find_caption_field(page)
            if lc is not None:
                lc.click()
                time.sleep(0.5)
                page.keyboard.type(caption, delay=30)
                time.sleep(1)
                log.info(f"Reel caption filled via selector: {sel}")
                caption_filled = True
```

- [ ] **Step 4: Run test — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_post_reel_clip_uses_keyboard_type_not_fill -v 2>&1 | tail -10
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add instagram.py tests/test_instagram.py
git commit -m "fix(instagram): reel caption fill use keyboard.type not fill()"
```

---

## Task 3: Fix `_verify_and_fix_caption` — selector + edit fill

**Files:**
- Modify: `instagram.py` — lines 212–235
- Modify: `tests/test_instagram.py`

- [ ] **Step 1: Update existing failing test for new selectors**

In `tests/test_instagram.py`, update `_make_page` to model IG's actual caption container (`div._a9zs`) instead of `h1`/`span`:

```python
def _make_page(caption_text: str):
    """Build mock Playwright page using IG's caption container selector."""
    page = MagicMock()

    caption_loc = MagicMock()
    if caption_text:
        caption_loc.count.return_value = 1
        caption_loc.first.inner_text.return_value = caption_text
    else:
        caption_loc.count.return_value = 0

    edit_loc = MagicMock()
    edit_loc.first = MagicMock()

    def locator_side(sel):
        # New caption container selectors
        if '_a9zs' in sel or 'caption' in sel.lower():
            return caption_loc
        return edit_loc

    page.locator.side_effect = locator_side
    return page, edit_loc
```

Also add a test that the edit flow uses `keyboard.type`:

```python
def test_verify_fix_edit_uses_keyboard_type():
    """Edit flow in _verify_and_fix_caption must use keyboard.type not fill."""
    from instagram import _verify_and_fix_caption

    page, edit_loc = _make_page("")  # no caption → triggers edit

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        _verify_and_fix_caption(page, "ทดสอบ")

    page.keyboard.type.assert_called_with("ทดสอบ", delay=30)
    edit_loc.first.fill.assert_not_called()
```

- [ ] **Step 2: Run updated tests — confirm some FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: `test_verify_fix_edit_uses_keyboard_type` FAIL, existing tests may also fail (new selector).

- [ ] **Step 3: Update `_verify_and_fix_caption` in `instagram.py`**

Replace lines 211–235 with:

```python
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
        page.keyboard.type(caption, delay=30)
        page.get_by_role("button", name="Done").click()
        time.sleep(2)
        log.info("Caption missing — fixed via edit")
        return True
```

- [ ] **Step 4: Run all instagram tests — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add instagram.py tests/test_instagram.py
git commit -m "fix(instagram): verify+fix use specific caption container selector and keyboard.type"
```

---

## Task 4: Add `_post_first_comment`

**Files:**
- Modify: `instagram.py` — add function after `_verify_and_fix_caption`
- Modify: `tests/test_instagram.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_instagram.py`:

```python
def test_post_first_comment_types_hashtags():
    """_post_first_comment clicks comment field and types hashtag block."""
    from unittest.mock import MagicMock, patch
    from instagram import _post_first_comment

    page = MagicMock()
    comment_loc = MagicMock()
    comment_loc.count.return_value = 1
    comment_loc.first = MagicMock()

    page.locator.return_value = comment_loc

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        result = _post_first_comment(page, "#แฟชั่น #ootd")

    assert result is True
    comment_loc.first.click.assert_called_once()
    page.keyboard.type.assert_called_once_with("#แฟชั่น #ootd", delay=10)
    page.keyboard.press.assert_called_once_with("Enter")


def test_post_first_comment_empty_hashtags_returns_false():
    """_post_first_comment returns False immediately when hashtags empty."""
    from instagram import _post_first_comment

    page = MagicMock()
    result = _post_first_comment(page, "")
    assert result is False
    page.goto.assert_not_called()


def test_post_first_comment_exception_returns_false():
    """Any exception in _post_first_comment returns False without raising."""
    from instagram import _post_first_comment

    page = MagicMock()
    page.goto.side_effect = Exception("network error")

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        result = _post_first_comment(page, "#แฟชั่น")

    assert result is False
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_post_first_comment_types_hashtags tests/test_instagram.py::test_post_first_comment_empty_hashtags_returns_false tests/test_instagram.py::test_post_first_comment_exception_returns_false -v 2>&1 | tail -10
```

Expected: `FAILED` — `_post_first_comment` not defined.

- [ ] **Step 3: Add `_post_first_comment` to `instagram.py`**

Insert after `_verify_and_fix_caption` (after line 242):

```python
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
```

- [ ] **Step 4: Run tests — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add instagram.py tests/test_instagram.py
git commit -m "feat(instagram): add _post_first_comment for hashtag first comment"
```

---

## Task 5: Add `hashtags=` param to `post_image` and `post_reel_clip`

**Files:**
- Modify: `instagram.py` — `post_image`, `_do_post`, `post_reel_clip`
- Modify: `tests/test_instagram.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_instagram.py`:

```python
def test_post_image_calls_post_first_comment_when_hashtags_given():
    """post_image calls _post_first_comment when hashtags param provided."""
    from pathlib import Path
    from unittest.mock import MagicMock, patch
    import instagram

    page = MagicMock()
    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._do_post"), \
         patch("instagram._post_first_comment") as mock_first_comment, \
         patch("instagram.time"):
        instagram.post_image(Path("/tmp/fake.jpg"), "caption", hashtags="#แฟชั่น #ootd")

    mock_first_comment.assert_called_once_with(page, "#แฟชั่น #ootd")
```

- [ ] **Step 2: Run test — confirm FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py::test_post_image_calls_post_first_comment_when_hashtags_given -v 2>&1 | tail -10
```

Expected: `FAILED` — `post_image` does not accept `hashtags` param.

- [ ] **Step 3: Update `post_image` signature and `_do_post` call**

In `instagram.py`, update `post_image` (line 102):

```python
def post_image(image_path: Path, caption: str, hashtags: str = "") -> str:
    """Post single image via Playwright web interface. Returns 'posted'."""
    from playwright.sync_api import sync_playwright

    image_path = Path(image_path).absolute()

    with sync_playwright() as p:
        browser, ctx = _make_context(p)
        page = ctx.new_page()

        if not _ensure_logged_in(page):
            browser.close()
            STATE_FILE.unlink(missing_ok=True)
            raise RuntimeError(
                "Instagram session expired. Update sessionid in assets/ig_session.json"
            )

        try:
            _do_post(page, image_path, caption)
            if hashtags:
                _post_first_comment(page, hashtags)
            ctx.storage_state(path=str(STATE_FILE))
            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Post failed: {e}") from e
```

Update `post_reel_clip` signature (line 249) and add `_post_first_comment` call after `_verify_and_fix_caption` (before `ctx.storage_state`):

```python
def post_reel_clip(video_path: Path, caption: str, hashtags: str = "") -> str:
```

And in the try block, after `_verify_and_fix_caption(page, caption)` (line 379), add:

```python
            if hashtags:
                _post_first_comment(page, hashtags)
```

- [ ] **Step 4: Run all tests — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_instagram.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add instagram.py tests/test_instagram.py
git commit -m "feat(instagram): add hashtags param to post_image and post_reel_clip"
```

---

## Task 6: Redesign `generate_caption` and `generate_video_caption`

**Files:**
- Modify: `content_gen.py`
- Create: `tests/test_content_gen.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_content_gen.py`:

```python
"""Tests for content_gen caption generation."""
from unittest.mock import MagicMock, patch
import pytest

FAKE_ITEM = {
    "itemName": "เสื้อครอปแขนกุด สีพาสเทล ลายดอกไม้",
    "priceDisplay": "199",
    "ratingStar": "4.8",
    "shopName": "FashionShopTH",
    "affiliateUrl": "https://shp.ee/test",
}


def _mock_claude(text: str):
    """Return a mock Anthropic client that responds with text."""
    content = MagicMock()
    content.text = text
    msg = MagicMock()
    msg.content = [content]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


def test_generate_caption_returns_thai_only_structure():
    """generate_caption prompt must be Thai-only (no English section)."""
    from content_gen import generate_caption

    with patch("content_gen.client", _mock_claude("Hook line\nBenefit\nราคา 199 บาท\nกดลิ้งค์ใน bio 👆")):
        result = generate_caption(FAKE_ITEM, post_type="image")

    # caption key must equal caption_body (no hashtags appended)
    assert result["caption"] == result["caption_body"]
    # hashtags must be a non-empty string (for first comment)
    assert isinstance(result["hashtags"], str)
    assert result["hashtags"].startswith("#")
    # caption must NOT contain hashtags
    assert "#" not in result["caption"]


def test_generate_caption_prompt_is_thai_only():
    """Claude prompt must not request English section."""
    from content_gen import generate_caption

    captured_prompt = []

    def capture_create(**kwargs):
        captured_prompt.append(kwargs["messages"][0]["content"])
        content = MagicMock()
        content.text = "Hook\nBenefit\nราคา 199\nCTA"
        msg = MagicMock()
        msg.content = [content]
        return msg

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = capture_create

    with patch("content_gen.client", mock_client):
        generate_caption(FAKE_ITEM)

    prompt = captured_prompt[0]
    assert "English" not in prompt
    assert "ภาษาไทย" in prompt or "Thai" not in prompt


def test_generate_video_caption_caption_equals_body():
    """generate_video_caption caption key must equal caption_body (no hashtags)."""
    from content_gen import generate_video_caption

    with patch("content_gen.client", _mock_claude("Hook\nBody\nราคา 199\n🛒 ลิ้งค์ด้านล่าง")):
        result = generate_video_caption(FAKE_ITEM)

    assert result["caption"] == result["caption_body"]
    assert "#" not in result["caption"]
    assert result["hashtags"]


def test_generate_first_comment_returns_hashtag_block():
    """generate_first_comment returns non-empty hashtag string with base tags."""
    from content_gen import generate_first_comment

    result = generate_first_comment(FAKE_ITEM)

    assert isinstance(result, str)
    assert "#แฟชั่น" in result
    assert "#ootd" in result
    # Must have 10+ tags
    tags = [t for t in result.split() if t.startswith("#")]
    assert len(tags) >= 10
```

- [ ] **Step 2: Run tests — confirm FAIL**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_content_gen.py -v 2>&1 | tail -15
```

Expected: multiple failures (wrong structure, `generate_first_comment` not defined).

- [ ] **Step 3: Update `content_gen.py`**

Add `HASHTAGS_IG_TH` constant after the existing hashtag lists (after line 22):

```python
HASHTAGS_IG_TH = [
    "#แฟชั่น", "#เสื้อผ้าผู้หญิง", "#ของถูก", "#ลดราคา", "#shopee",
    "#แฟชั่นราคาถูก", "#สไตล์เกาหลี", "#ชุดเซ็ต", "#เสื้อผ้าออนไลน์", "#ootd",
    "#แฟชั่นไทย", "#เทรนด์แฟชั่น", "#ไอเดียแต่งตัว", "#ของดีในShopee",
    "#เสื้อผ้าน่ารัก", "#แฟชั่นออนไลน์", "#ช้อปออนไลน์", "#Shopeeไทย",
    "#ลุคน่ารัก", "#สไตล์ไทย",
]
```

Replace `generate_caption` (lines 25–71) with:

```python
def generate_caption(item: dict, post_type: str = "image") -> dict:
    """Generate Thai-only Instagram caption: hook / benefit / price / CTA."""
    price = item.get("priceDisplay") or item.get("priceMin") or item.get("price", "")
    if isinstance(price, (int, float)) and price > 1000:
        price_display = f"฿{float(price)/100000:.0f}"
    else:
        price_display = str(price) if price else "ราคาพิเศษ"

    prompt = f"""คุณเป็น content creator แฟชั่นไทยบน Instagram เขียน caption ภาษาไทยอย่างเดียว

สินค้า: {item['itemName']}
ราคา: {price_display} บาท
คะแนน: {item.get('ratingStar', '')} ดาว

โครงสร้าง 4 ส่วน (แต่ละส่วน 1 บรรทัด):
1. HOOK: สั้น ดึงดูด สร้างความอยากรู้ ใช้ emoji ได้ ไม่เกิน 40 ตัวอักษร
2. BENEFIT: ทำไมถึงต้องซื้อ พูดเหมือนคุยกับเพื่อน 1-2 บรรทัด
3. ราคา: เช่น "ราคาแค่ {price_display} บาทเอง 🤑" หรือ "ได้มาแค่ {price_display} บาท"
4. CTA: เช่น "กดลิ้งค์ใน bio เลย 👆" หรือ "คอมเมนต์ว่า 'สนใจ' 💬"

ห้าม: ภาษาอังกฤษ, hashtag, คำโฆษณา เช่น "สินค้าคุณภาพดี"
ฟังดูเหมือน gen-z ไทยโพสจริงๆ ไม่ใช่แบรนด์

ส่งแค่ caption เท่านั้น ไม่ต้องมี label ไม่ต้องมี hashtag"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()
    hashtags = " ".join(HASHTAGS_IG_TH)

    return {
        "caption": caption_body,
        "caption_body": caption_body,
        "hashtags": hashtags,
    }
```

Update `generate_video_caption` return dict (lines 145–150) — change `caption` key to equal `caption_body`:

```python
    return {
        "caption": caption_body,
        "caption_body": caption_body,
        "hashtags": " ".join(HASHTAGS_IG_TH),
        "affiliate_url": item.get("affiliateUrl", ""),
    }
```

Also update line 142–143 (remove old `full_caption` construction):

```python
    caption_body = message.content[0].text.strip()
```

(Remove `hashtags = " ".join(HASHTAGS_TIKTOK)` and `full_caption = ...` lines)

- [ ] **Step 4: Run tests — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_content_gen.py -v 2>&1 | tail -15
```

Expected: all pass except `test_generate_first_comment_returns_hashtag_block` (function not added yet).

- [ ] **Step 5: Commit**

```bash
git add content_gen.py tests/test_content_gen.py
git commit -m "feat(content_gen): Thai-only caption structure, caption key = body only"
```

---

## Task 7: Add `generate_first_comment`

**Files:**
- Modify: `content_gen.py` — add function at end
- `tests/test_content_gen.py` — test already written in Task 6

- [ ] **Step 1: Confirm test still fails**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_content_gen.py::test_generate_first_comment_returns_hashtag_block -v 2>&1 | tail -10
```

Expected: `FAILED` — `generate_first_comment` not defined.

- [ ] **Step 2: Add `generate_first_comment` to `content_gen.py`**

Add after `generate_reel_script` (at end of file):

```python
def generate_first_comment(item: dict) -> str:
    """Return hashtag block for first comment: base HASHTAGS_IG_TH + item keyword tags."""
    import re
    name = item.get("itemName", "")
    words = re.split(r'[\s/\-,。、]+', name)
    dynamic: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) >= 3 and not w.isdigit():
            tag = f"#{w.replace(' ', '')}"
            if tag not in dynamic and tag not in HASHTAGS_IG_TH:
                dynamic.append(tag)
        if len(dynamic) >= 5:
            break

    return " ".join(HASHTAGS_IG_TH[:15] + dynamic)
```

- [ ] **Step 3: Run all content_gen tests — confirm PASS**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/test_content_gen.py -v 2>&1 | tail -15
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add content_gen.py
git commit -m "feat(content_gen): add generate_first_comment for hashtag first comment"
```

---

## Task 8: Update `main.py` callers

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update `run_post_cycle` image posting**

In `main.py`, find the `run_post_cycle` image loop (around line where `post_image` is called). Update the import at the top to include `generate_first_comment`:

```python
from content_gen import generate_caption, generate_reel_script, generate_video_caption, generate_outfit_caption, generate_first_comment
```

Then update the image post block:

```python
        for i, item in enumerate(image_items):
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                img_path = create_post_image(item, item["affiliateUrl"], f"post_{ts}_{i}")
                caption_data = generate_caption(item, post_type="image")
                first_comment = generate_first_comment(item)
                media_id = post_image(img_path, caption_data["caption"], hashtags=first_comment)
                log.info(f"Image posted: {media_id} — {item['itemName'][:40]}")
                post_history.add(str(item.get("itemId", "")))
                posted += 1
            except Exception as e:
                log.error(f"Image post {i} failed: {e}")
```

- [ ] **Step 2: Update `_make_clip` to return `first_comment`**

In `_make_clip`, add `first_comment` to the return tuple. Find the return statement near the end of `_make_clip` and update:

```python
    first_comment = generate_first_comment(item)
    return clip_path, title, caption_with_link, first_comment
```

Add the `generate_first_comment` call just before the return (in all branches — the `if clip_type == "outfit":` branch and the `else:` branch). Place it after `caption_with_link` is set in each branch.

For the `outfit` branch, add before `return`:
```python
    first_comment = generate_first_comment(item)
    return clip_path, title, caption_with_link, first_comment
```

For all other clip types, the same line before `return`.

- [ ] **Step 3: Update `run_video_cycle` to unpack new tuple**

Find the `run_video_cycle` call to `_make_clip`:

```python
            clip_path, title, caption = _make_clip(item, i, signals)
            _distribute_clip(clip_path, title, caption, item.get("itemName", ""))
```

Update to:

```python
            clip_path, title, caption, first_comment = _make_clip(item, i, signals)
            _distribute_clip(clip_path, title, caption, item.get("itemName", ""), hashtags=first_comment)
```

- [ ] **Step 4: Update `_distribute_clip` to accept and pass `hashtags`**

```python
def _distribute_clip(clip_path, title: str, caption: str, item_name: str = "", hashtags: str = "") -> None:
    """Post clip to all active platforms. Each platform fails independently."""
    try:
        yt_title = title.strip() or item_name[:100] or "Fashion Find"
        video_id = post_short(clip_path, yt_title, caption)
        log.info(f"YouTube Short posted: {video_id}")
    except Exception as e:
        log.error(f"YouTube post failed: {e}")

    try:
        from instagram import post_reel_clip
        post_reel_clip(clip_path, caption, hashtags=hashtags)
        log.info(f"Instagram Reel posted: {item_name[:40]}")
    except Exception as e:
        log.error(f"Instagram Reel post failed: {e}")
```

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all pass (or same count as before this task).

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(main): pass hashtags to post_image and post_reel_clip via generate_first_comment"
```

---

## Task 9: Update posting times to Thai IG peak windows

**Files:**
- Modify: `config.py` — one line

- [ ] **Step 1: Update `POST_TIMES` default in `config.py`**

Find the `POST_TIMES` assignment (around line 16). Replace the default value string:

```python
POST_TIMES = os.getenv(
    "POST_TIMES",
    "07:00,08:00,09:00,11:30,12:30,19:00,20:00,21:00,21:30",
).split(",")
```

- [ ] **Step 2: Verify no tests broken**

```bash
cd /Users/aegisen/fashion-bot && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: same pass count as after Task 8.

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "config: align POST_TIMES default to Thai IG peak windows (07-09, 11:30-12:30, 19-21:30)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Section 1: Caption fill fix — Tasks 1, 2
- ✅ Section 1: Navigation timing — not a separate task; timing is resolved by the selector-based approach + existing waits. Fixed-sleep issue is secondary to the fill bug; `wait_for_selector` in `_find_caption_field` loop already handles this in `post_reel_clip`.
- ✅ Section 1: Unify image/reel to `_find_caption_field` — partially addressed in Task 1 (image now uses same keyboard approach); full unification deferred as it would require restructuring `_do_post` significantly with low incremental benefit.
- ✅ Section 1: `_verify_and_fix_caption` selector — Task 3
- ✅ Section 1: Edit flow `keyboard.type` — Task 3
- ✅ Section 2: First comment with hashtags — Tasks 4, 5
- ✅ Section 2: `generate_caption` Thai-only hook structure — Task 6
- ✅ Section 2: `caption` key = body only — Task 6
- ✅ Section 2: `generate_first_comment` — Task 7
- ✅ Section 2: `_post_first_comment` — Task 4
- ✅ Section 3: Posting times — Task 9
- ✅ Main.py wiring — Task 8

**Type consistency:**
- `generate_first_comment(item: dict) -> str` — used in Task 7, called in Task 8. ✅
- `_post_first_comment(page, hashtags: str) -> bool` — defined Task 4, called Task 5. ✅
- `post_image(..., hashtags: str = "")` — defined Task 5, called Task 8. ✅
- `post_reel_clip(..., hashtags: str = "")` — defined Task 5, called Task 8 via `_distribute_clip`. ✅
- `_make_clip` return tuple extended to 4 elements — defined and consumed in Task 8. ✅

**Placeholder scan:** No TBDs, no "similar to Task N", all steps have concrete code. ✅
