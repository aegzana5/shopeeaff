# Viral Trend Repost & Affiliate Pipeline

**Date:** 2026-05-08
**Status:** Approved

## Goal

Discover viral Thai fashion posts on TikTok and Instagram, reshare them to Stories/Repost natively, and when a Shopee product match is found for the featured item, generate a new original affiliate clip and post it to all platforms.

## Architecture

```
trend_discovery.py   find viral posts (Instagram via instagrapi, TikTok via TikTokApi)
trend_reshare.py     reshare to Instagram Stories + TikTok Repost; find Shopee match;
                     generate + post affiliate clip
trend_signals.py     extract caption hooks + clip format hints → trend_signals.json
shopee.py            new search_products(query) function
main.py              new run_trend_cycle() wired into APScheduler every 6 hours
config.py            accounts list, hashtag list, thresholds, feature flags
.env.example         new keys documented
requirements.txt     TikTokApi added
tests/               3 new test files
```

### Data flow

```
run_trend_cycle()
  → discover_all()             → list[post_dict]
  → for each post:
      reshare_story(post)      → Instagram Story reshare / TikTok Repost
      match = find_shopee_match(post)
      if match:
          clip = generate_affiliate_clip(match, post)
          post_affiliate_clip(clip, match)
  → extract_signals(posts)    → assets/trend_signals.json

run_video_cycle() (existing, unchanged interface)
  → reads trend_signals.json
  → biases CLIP_TYPES toward top_clip_types
  → passes hooks as extra context to generate_video_caption()
```

### Post dict schema

```python
{
    "platform":     "instagram" | "tiktok",
    "post_id":      str,
    "url":          str,
    "caption":      str,
    "views":        int,
    "likes":        int,
    "source":       str,   # account username or hashtag string
    "source_type":  "account" | "hashtag",
}
```

## Components

### `trend_discovery.py`

```python
discover_instagram(accounts: list[str], hashtags: list[str]) -> list[dict]
discover_tiktok(accounts: list[str], hashtags: list[str]) -> list[dict]
discover_all() -> list[dict]
```

**`discover_instagram`:**
- For each account: `cl.user_id_from_username(name)` → `cl.user_medias(uid, amount=20)` → filter
- For each hashtag: `cl.hashtag_medias_top(tag, amount=20)` → filter
- Filter: top `TREND_TOP_N` posts where `views >= TREND_MIN_VIEWS OR likes >= TREND_MIN_LIKES`
- Returns `list[post_dict]`; returns `[]` on any instagrapi error (logs warning)

**`discover_tiktok`:**
- Requires `TikTokApi` installed; if import fails returns `[]` (logs warning, `TIKTOKAPI_ENABLED` flag)
- For each account: `api.user(username=name).videos(count=20)` → filter
- For each hashtag: `api.hashtag(name=tag).videos(count=20)` → filter
- Same threshold filter as Instagram
- Returns `list[post_dict]`

**`discover_all`:**
- Reads `TREND_ACCOUNTS_INSTAGRAM`, `TREND_ACCOUNTS_TIKTOK`, `TREND_HASHTAGS` from config
- Calls both discover functions, deduplicates by `post_id`, returns combined list

### `trend_reshare.py`

```python
reshare_story(post: dict) -> bool
find_shopee_match(post: dict) -> dict | None
generate_affiliate_clip(item: dict, post: dict) -> Path
post_affiliate_clip(clip_path: Path, item: dict) -> None
```

**`reshare_story`:**
- Instagram posts: `cl.story_reshare(media_pk=post["post_id"])` via instagrapi
- TikTok posts: Playwright navigates to `post["url"]`, clicks Share → Repost button
- Returns `False` and logs warning on any failure; never raises

**`find_shopee_match`:**
- Uses Claude (`anthropic` client, `claude-haiku-4-5-20251001`) to extract product search query from `post["caption"]` (1–4 English/Thai keywords)
- Calls `shopee.search_products(query)` → returns first result or `None`
- Returns `None` if caption yields no usable keywords or search returns empty

**`generate_affiliate_clip`:**
- Infers clip format from post caption:
  - "ก่อน" / "หลัง" → `create_before_after_clip`
  - "POV" → `create_pov_meme_clip`
  - "ราคา" / "price" → `create_price_shock_clip`
  - default → `create_beat_hook_clip`
- Generates output name `trend_{post_id}`
- Calls the matching `viral_gen` function with `item`

**`post_affiliate_clip`:**
- Posts via existing pipeline: `post_clip` (TikTok), `post_short` (YouTube), `post_reel_clip` (Instagram Reel)
- Caption from `generate_video_caption(item)`
- Each platform wrapped in try/except; failures logged, others continue

### `trend_signals.py`

```python
extract_signals(posts: list[dict]) -> dict
save_signals(signals: dict) -> None
load_signals() -> dict
```

**`extract_signals`:**
- `hooks`: first non-empty line of each caption, deduplicated, max 10
- `top_clip_types`: keyword map on all captions:
  - "ก่อน"/"หลัง" → `before_after`
  - "POV" → `pov_meme`
  - "ราคา"/"price"/"shock" → `price_shock`
  - "beat"/"เสียง" → `beat_hook`
  - unmatched → `multi`
  - returns top 3 by frequency
- `trending_hashtags`: all `#tag` tokens from captions, top 10 by frequency

**`save_signals`:** writes `assets/trend_signals.json` atomically (tmp + rename)

**`load_signals`:** returns `{}` if file missing (no crash)

### `shopee.py` addition

```python
search_products(query: str) -> list[dict]
```

- GET Shopee search API with `query` string
- Returns same item dict format as `get_trending_fashion()` (same fields: `itemName`, `price`, `priceDisplay`, `imageUrl`, `affiliateUrl`, `itemId`)
- Returns `[]` on HTTP error (logs warning)

### `main.py` changes

New function `run_trend_cycle()`:
```python
def run_trend_cycle():
    posts = discover_all()
    if not posts:
        return
    for post in posts:
        try:
            if TREND_RESHARE_ENABLED:
                reshare_story(post)
            item = find_shopee_match(post)
            if item:
                clip = generate_affiliate_clip(item, post)
                post_affiliate_clip(clip, item)
        except Exception as e:
            log.error(f"Trend post {post['post_id']} failed: {e}")
    signals = extract_signals(posts)
    save_signals(signals)
```

APScheduler: add `run_trend_cycle` job every 6 hours alongside existing jobs.

`run_video_cycle` reads `trend_signals.json` at start of each cycle:
- If `top_clip_types` present: append each type from `top_clip_types` once to `CLIP_TYPES` before `random.choice` (duplicating increases probability proportionally, e.g. `["multi", ..., "price_shock", "price_shock"]`)
- If `hooks` present: pass as `extra_hooks` kwarg to `generate_video_caption()`

`generate_video_caption` in `content_gen.py`: accept optional `extra_hooks: list[str] = None`; if provided, include in Claude prompt as "trending hooks to consider".

### `config.py` additions

```python
TREND_ACCOUNTS_INSTAGRAM = [a for a in os.getenv("TREND_ACCOUNTS_INSTAGRAM", "").split(",") if a]
TREND_ACCOUNTS_TIKTOK    = [a for a in os.getenv("TREND_ACCOUNTS_TIKTOK", "").split(",") if a]
TREND_HASHTAGS           = [h for h in os.getenv("TREND_HASHTAGS", "แฟชั่น,ootdthailand,shopee_th").split(",") if h]
TREND_MIN_VIEWS          = int(os.getenv("TREND_MIN_VIEWS", "10000"))
TREND_MIN_LIKES          = int(os.getenv("TREND_MIN_LIKES", "1000"))
TREND_TOP_N              = int(os.getenv("TREND_TOP_N", "3"))
TREND_RESHARE_ENABLED    = os.getenv("TREND_RESHARE_ENABLED", "true").lower() == "true"
TIKTOKAPI_ENABLED        = os.getenv("TIKTOKAPI_ENABLED", "true").lower() == "true"
```

## Error Handling

| Failure | Behavior |
|---------|----------|
| TikTokApi import fails | Log warning, `discover_tiktok` returns `[]`, cycle continues |
| instagrapi account not found | Log warning, skip that account |
| instagrapi rate limit | Log warning, skip Instagram discovery this cycle |
| Story reshare fails | Log warning, continue to next post |
| TikTok Repost fails | Log warning, continue |
| Claude keyword extraction fails | `find_shopee_match` returns `None` |
| Shopee search returns empty | `find_shopee_match` returns `None` |
| Clip generation fails | Log error, skip affiliate post for this item |
| Platform posting fails | Log error per platform, others continue |
| No posts discovered | Log info, no signals written, `run_video_cycle` uses defaults |
| `trend_signals.json` missing | `load_signals()` returns `{}`, no crash |

## Testing

| File | What it tests |
|------|---------------|
| `tests/test_trend_discovery.py` | Mock instagrapi + TikTokApi; assert threshold filter applied; assert `[]` on import error |
| `tests/test_trend_reshare.py` | Mock `cl.story_reshare` + Playwright; mock `search_products`; assert affiliate clip generated when match found; assert `None` path skips clip |
| `tests/test_trend_signals.py` | Assert hook/clip-type/hashtag extraction from sample Thai + English captions; assert `load_signals()` returns `{}` on missing file |

## New Dependencies

```
TikTokApi>=6.0.0    unofficial TikTok client (Playwright-backed)
```

Add to `requirements.txt`.

## Files Changed

| File | Action |
|------|--------|
| `trend_discovery.py` | New |
| `trend_reshare.py` | New |
| `trend_signals.py` | New |
| `shopee.py` | Updated — add `search_products()` |
| `content_gen.py` | Updated — `generate_video_caption()` accepts `extra_hooks` |
| `main.py` | Updated — `run_trend_cycle()`, scheduler, `run_video_cycle` reads signals |
| `config.py` | Updated — 8 new env vars |
| `.env.example` | Updated — new vars documented |
| `requirements.txt` | Updated — TikTokApi |
| `tests/test_trend_discovery.py` | New |
| `tests/test_trend_reshare.py` | New |
| `tests/test_trend_signals.py` | New |

## Success Criteria

- `run_trend_cycle()` completes without error when all APIs return empty
- Viral post with identifiable product → affiliate clip posted to TikTok + Instagram + YouTube
- Viral post with no Shopee match → Story reshare only, no clip generated
- TikTokApi unavailable → Instagram-only discovery, no crash
- `run_video_cycle` clip type distribution shifts when `trend_signals.json` present
- All existing tests still pass
