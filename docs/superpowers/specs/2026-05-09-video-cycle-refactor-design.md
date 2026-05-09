# Design: run_video_cycle Refactor

**Date:** 2026-05-09  
**Status:** Approved

## Problem

`run_video_cycle()` in `main.py` is a 90-line god function that owns three distinct concerns in one block: data fetching + dedup, clip creation, and multi-platform distribution. Adding or removing a platform requires editing the entire function. The graphify graph confirmed it bridges 5 separate communities (Caption Gen, FFmpeg Pipeline, Outfit Matching, YouTube Upload, Instagram Playwright).

## Design

Split `run_video_cycle()` into three private helpers that each have one job. All three stay in `main.py` — no new files.

### `_fetch_clip_items() -> list`

Responsibility: load signals, fetch Shopee trending items, deduplicate against video history, return a list of fresh items up to `CLIPS_PER_DAY`.

- Calls `load_signals()`, `get_trending_fashion()`, `pick_top_items()`
- Loads and returns history set; does NOT save (saving stays in `run_video_cycle` after the loop so partial runs still persist)
- Resets history if exhausted (existing behaviour preserved)

### `_make_clip(item: dict, i: int, trending_hooks: list) -> tuple[Path, str, str]`

Responsibility: select clip type, generate caption, run TTS, build the video file. Returns `(clip_path, title, caption_with_link)`.

- Contains the full `if clip_type == "outfit": ... else: ...` branch
- Raises on failure — caller catches at the cycle level

### `_distribute_clip(clip_path: Path, title: str, caption: str) -> None`

Responsibility: post to all active platforms. Currently YouTube Short + Instagram Reel.

- Calls `post_short(clip_path, title, caption)` → logs result
- Calls `post_reel_clip(clip_path, caption)` → logs result
- Each platform wrapped in its own try/except so one failure doesn't skip the other

### `run_video_cycle()` — thin orchestrator

```python
def run_video_cycle():
    log.info("Starting video cycle")
    trending_hooks = load_signals().get("hooks", [])
    items, history = _fetch_clip_items()
    posted = 0
    for i, item in enumerate(items):
        try:
            clip_path, title, caption = _make_clip(item, i, trending_hooks)
            _distribute_clip(clip_path, title, caption)
            history.add(str(item.get("itemId", "")))
            posted += 1
        except Exception as e:
            log.error(f"Video clip {i} failed: {e}")
    _save_video_history(history)
    log.info(f"Video cycle done: {posted}/{CLIPS_PER_DAY} clips")
```

Note: `_fetch_clip_items()` returns `(items, history)` so the caller can update and save history after the loop.

## What Does NOT Change

- All existing logic preserved verbatim — this is structural only
- `CLIP_TYPES` weighting, signal injection, outfit matcher, TTS, stock media calls — unchanged
- `run_post_cycle()` and `run_trend_cycle()` — untouched
- Error handling semantics — unchanged

## Testing

Existing test suite (57 tests) must still pass. No new tests required — this is a pure structural refactor with no logic changes.

## Out of Scope

- Extracting a `publisher.py` module (user chose to keep in main.py)
- Refactoring `run_post_cycle()` or `run_trend_cycle()`
- Adding new platforms
