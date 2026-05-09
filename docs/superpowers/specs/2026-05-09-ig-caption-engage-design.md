# Instagram Caption Fix + Engagement Improvement Design

**Date:** 2026-05-09  
**Scope:** Bug fix (caption not posted) + caption quality + posting time optimization  
**Files:** `instagram.py`, `content_gen.py`, `config.py`

---

## Problem

1. **Caption not added to posts/reels** — `.fill()` on IG's `contenteditable` React editor injects a DOM value without triggering React's synthetic events. IG sees an empty field and publishes with no caption.
2. **Verify+fix selector too broad** — `[role="dialog"] h1` / `span` matches username and location, falsely reports caption as present and skips the fix.
3. **Caption content not optimized** — flat unstructured text, no hook, hashtags missing or buried, no CTA.
4. **Posting times not peak-aligned** — fixed slots spread across the day miss Thai IG peak windows.

---

## Section 1: Caption Bug Fix (`instagram.py`)

### Fill method

Replace `.fill(caption)` with:
```python
field.click()
page.keyboard.type(caption, delay=30)
```
Fires real keystrokes → React synthetic events fire → IG registers the caption.

Apply to both `_do_post` (image) and `post_reel_clip` (reel).

### Navigation timing

Replace fixed `time.sleep(2)` between Next steps with:
```python
page.wait_for_selector(caption_sel, timeout=3000)
```
Fall back to `time.sleep(2)` only if selector not found. Adapts to IG's variable load speed.

### Unify caption field search

Both `_do_post` and `post_reel_clip` use `_find_caption_field` (frame-aware search across all frames). Remove the simpler selector-only path in `_do_post`.

### Verify+fix selector

Replace `[role="dialog"] h1` / `span` with IG's actual caption container:
```
[role="dialog"] div._a9zs, [role="dialog"] article div[class*="caption"]
```
Fallback: if container empty AND post timestamp < 60s ago, always attempt edit (recent post = likely ours).

Edit flow fill also uses `keyboard.type()`.

---

## Section 2: Caption Quality Redesign (`content_gen.py`, `instagram.py`)

### Caption structure (Thai-only)

```
[HOOK — 1 punchy line, curiosity or urgency]
[BENEFIT — 1-2 lines, why this product is worth buying]
[PRICE ANCHOR — "ราคา XXX บาท" or "ลด XX%"]
[CTA — "กดลิงก์ในไบโอ" or "คอมเมนต์ว่า 'สนใจ'"]
```

### First comment (hashtags)

Hashtags posted as first comment after share — algo indexes them, caption stays readable.

**Base tags (always included):**
```
#แฟชั่น #เสื้อผ้าผู้หญิง #ของถูก #ลดราคา #shopee #แฟชั่นราคาถูก #สไตล์เกาหลี #ชุดเซ็ต #เสื้อผ้าออนไลน์ #ootd
```

**Dynamic tags:** 3–5 keyword tags extracted from item name via Claude (Thai keyword split).

Total: 15–20 tags per post.

### `content_gen.py` changes

- Rewrite Claude system prompt for `generate_caption()` and `generate_video_caption()` to enforce the hook/benefit/price/CTA structure.
- Return dict with separate keys: `caption_body` (no hashtags) and `hashtags` (list of strings).
- Add `generate_first_comment(item) -> str` — returns hashtag block only.

### `instagram.py` changes

- After successful post/reel share, call `_post_first_comment(page, hashtags: str)`.
- `_post_first_comment` navigates to the most recent post, clicks the comment input, types the hashtag block, submits.
- Non-fatal: failure logs warning, does not raise.

---

## Section 3: Posting Time Optimization (`config.py`)

**Thai IG peak windows (Bangkok, UTC+7):**
- Morning: 07:00–09:00
- Lunch: 11:30–13:00
- Evening: 19:00–21:30

**New default `POST_TIMES`:**
```
07:00, 08:00, 09:00, 11:30, 12:30, 19:00, 20:00, 21:00, 21:30
```

9 slots, all within peak windows. `.env` override still respected.

---

## Data Flow

```
run_post_cycle / run_video_cycle
  → generate_caption(item)
      returns {caption_body, hashtags}
  → post_image / post_reel_clip (caption_body only)
      → keyboard.type(caption_body)           ← fix
      → _verify_and_fix_caption (tightened)   ← fix
      → _post_first_comment(hashtags)         ← new
```

---

## Error Handling

- Caption fill failure → log warning, post proceeds (caption may be empty)
- Verify+fix failure → log warning, non-fatal
- First comment failure → log warning, non-fatal (post already live)
- All Playwright errors caught per-function, never propagate to crash the cycle

---

## Testing

- Update `test_instagram.py`: add tests for `_post_first_comment` (mock page, assert comment typed and submitted)
- Update `test_instagram.py`: update verify+fix tests to use new caption container selector
- Update `content_gen.py` tests: assert returned dict has `caption_body` and `hashtags` keys
- No test for posting times (config-only change)
