# run_video_cycle Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 90-line `run_video_cycle()` god function into three private helpers — `_fetch_clip_items`, `_make_clip`, `_distribute_clip` — each with one responsibility, all staying in `main.py`.

**Architecture:** Pure structural refactor. Logic moves verbatim into helpers; `run_video_cycle()` becomes a thin loop. No new files, no behaviour changes.

**Tech Stack:** Python 3.14, pytest (existing test suite)

---

## File Map

| File | Change |
|------|--------|
| `main.py` | Add 3 private helpers above `run_video_cycle()`; replace body with thin orchestrator |

---

### Task 1: Confirm green baseline

**Files:**
- Run: `tests/`

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/python3 -m pytest tests/ -v 2>&1 | tail -10
```

Expected: `57 passed` (4 TikTok tests skipped — that's fine).

- [ ] **Step 2: Commit nothing** — baseline confirmed, proceed to Task 2.

---

### Task 2: Extract `_fetch_clip_items`

**Files:**
- Modify: `main.py` (add helper above `run_video_cycle`)

- [ ] **Step 1: Add `_fetch_clip_items` above `run_video_cycle` in `main.py`**

Insert this function directly above `def run_video_cycle():`:

```python
def _fetch_clip_items() -> tuple[list, set]:
    """Return (fresh_items_up_to_CLIPS_PER_DAY, history_set)."""
    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee feed")
        return [], set()

    history = _load_video_history()
    all_items = pick_top_items(items, n=min(len(items), 200))
    fresh = [it for it in all_items if str(it.get("itemId", "")) not in history]

    if len(fresh) < CLIPS_PER_DAY:
        log.warning("Video history nearly exhausted, resetting")
        history = set()
        fresh = all_items

    return fresh[:CLIPS_PER_DAY], history
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `57 passed` — helper is defined but not yet called, nothing broken.

---

### Task 3: Extract `_make_clip`

**Files:**
- Modify: `main.py` (add helper above `run_video_cycle`)

- [ ] **Step 1: Add `_make_clip` above `run_video_cycle` in `main.py`**

Insert directly above `def run_video_cycle():` (after `_fetch_clip_items`):

```python
def _make_clip(item: dict, i: int, signals: dict) -> tuple:
    """Build one video clip. Returns (clip_path, title, caption_with_link)."""
    trending_hooks = signals.get("hooks", [])
    top_clip_types = signals.get("top_clip_types", [])

    CLIP_TYPES = [
        "price_reveal", "before_after", "pov_meme", "price_shock", "beat_hook",
        "outfit", "outfit",
    ]
    CLIP_TYPES = CLIP_TYPES + top_clip_types

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clip_type = random.choice(CLIP_TYPES)
    clip_name = f"clip_{ts}_{i}"

    if clip_type == "outfit":
        from outfit_matcher import find_outfit_matches
        from image_ai import generate_model_image, remove_bg
        matches = find_outfit_matches(item, n=OUTFIT_MATCHES)
        caption_data = generate_outfit_caption(item, matches)
        caption = caption_data["caption"]
        caption_body = caption_data.get("caption_body", caption)
        title = item["itemName"][:100]
        caption_with_link = caption_data.get("caption_with_links", caption)
        vo_path = tts.generate_voiceover_from_text(caption_body, clip_name)
        model_img = generate_model_image(item, clip_name) or remove_bg(item.get("imageUrl", ""), clip_name)
        clip_path = create_outfit_clip(
            item, matches, clip_name,
            model_image_path=model_img,
            voiceover_path=vo_path,
        )
    else:
        caption_data = generate_video_caption(item, extra_hooks=trending_hooks or None)
        caption = caption_data["caption"]
        caption_body = caption_data.get("caption_body", caption)
        title = item["itemName"][:100]
        affiliate_url = caption_data.get("affiliate_url", "")
        caption_with_link = _inject_link(caption, affiliate_url)
        vo_path = tts.generate_voiceover_from_text(caption_body, clip_name)
        keywords = stock_media._extract_keywords(item["itemName"])
        bg_path = stock_media.fetch_bg_video(keywords, clip_name)
        if clip_type == "before_after":
            clip_path = create_before_after_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "pov_meme":
            clip_path = create_pov_meme_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "price_shock":
            clip_path = create_price_shock_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "beat_hook":
            clip_path = create_beat_hook_clip(item, clip_name, voiceover_path=vo_path)
        else:
            clip_path = create_price_reveal_clip(
                item, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
            )

    return clip_path, title, caption_with_link
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `57 passed`.

---

### Task 4: Extract `_distribute_clip`

**Files:**
- Modify: `main.py` (add helper above `run_video_cycle`)

- [ ] **Step 1: Add `_distribute_clip` above `run_video_cycle` in `main.py`**

Insert directly above `def run_video_cycle():` (after `_make_clip`):

```python
def _distribute_clip(clip_path, title: str, caption: str, item_name: str = "") -> None:
    """Post clip to all active platforms. Each platform fails independently."""
    try:
        yt_title = title.strip() or item_name[:100] or "Fashion Find"
        video_id = post_short(clip_path, yt_title, caption)
        log.info(f"YouTube Short posted: {video_id}")
    except Exception as e:
        log.error(f"YouTube post failed: {e}")

    try:
        from instagram import post_reel_clip
        post_reel_clip(clip_path, caption)
        log.info(f"Instagram Reel posted: {item_name[:40]}")
    except Exception as e:
        log.error(f"Instagram Reel post failed: {e}")
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: `57 passed`.

---

### Task 5: Replace `run_video_cycle` body with thin orchestrator

**Files:**
- Modify: `main.py` — replace `run_video_cycle` body

- [ ] **Step 1: Replace `run_video_cycle` body**

Replace the entire body of `run_video_cycle()` (everything after `def run_video_cycle():`) with:

```python
def run_video_cycle():
    log.info("Starting video cycle")

    signals = load_signals()
    clip_items, history = _fetch_clip_items()
    if not clip_items:
        return

    posted = 0
    for i, item in enumerate(clip_items):
        try:
            clip_path, title, caption = _make_clip(item, i, signals)
            _distribute_clip(clip_path, title, caption, item.get("itemName", ""))
            history.add(str(item.get("itemId", "")))
            posted += 1
        except Exception as e:
            log.error(f"Video clip {i} failed: {e}")

    _save_video_history(history)
    log.info(f"Video cycle done: {posted}/{CLIPS_PER_DAY} clips")
```

- [ ] **Step 2: Run full test suite**

```bash
.venv/bin/python3 -m pytest tests/ -v 2>&1 | tail -15
```

Expected: `57 passed`. If any fail, check that the old body was fully removed and replaced.

- [ ] **Step 3: Verify `run_video_cycle` has no leftover old code**

```bash
grep -n "CLIP_TYPES\|clip_type\|clip_name\|caption_data\|vo_path\|bg_path" main.py
```

Expected: all matches inside `_make_clip`, none inside `run_video_cycle`.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "refactor(main): split run_video_cycle into fetch/make/distribute helpers"
```

- [ ] **Step 5: Push**

```bash
git push
```
