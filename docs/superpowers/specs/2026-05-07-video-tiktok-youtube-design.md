# Video Generation + TikTok/YouTube Shorts Integration

**Date:** 2026-05-07
**Account:** @trendyinthai

## Goal

Generate 7-second product showcase clips from Shopee affiliate items and post to TikTok and YouTube Shorts. Simultaneously simplify Instagram posts to clean product-only images.

## Architecture

```
Shopee item (image URL + metadata)
  └→ video_gen.py: Pillow frames → FFmpeg → 1080×1920 MP4 (7s)
        ├→ tiktok.py: Playwright upload
        └→ youtube.py: YouTube Data API v3 upload

media_gen.create_post_image → simplified: center-crop to 1080×1080
```

## Files Changed

| File | Action |
|------|--------|
| `video_gen.py` | New — Pillow frame renderer + FFmpeg encoder |
| `tiktok.py` | New — Playwright-based TikTok upload |
| `youtube.py` | New — YouTube Data API v3 upload |
| `media_gen.py` | Modify `create_post_image` — remove overlays, center-crop only |
| `main.py` | Add `run_video_cycle()` |
| `config.py` | Add `CLIPS_PER_DAY`, `YOUTUBE_TOKEN_FILE` |
| `requirements.txt` | Add `google-api-python-client`, `google-auth-oauthlib` |
| `assets/music/` | Add 3 CC0 royalty-free tracks |

## Part 1: Instagram — Minimal Posts

`create_post_image` simplified to:
1. Download product image
2. Center-crop to 1080×1080 (crop to fill, no letterboxing, no overlays)
3. Save as JPEG

No brand strip. No info bar. No text overlays. Caption carries all product info.

## Part 2: video_gen.py

### Video spec
- Resolution: 1080×1920 (9:16)
- Duration: 7s at 30fps = 210 frames
- Output: `assets/output/clip_<ts>.mp4`

### Frame composition (Pillow)
1. **Background:** product image scaled to fill 1080×1920, Gaussian blur radius 30
2. **Product:** product image scaled to fit within 1080×1400 (centered horizontally, vertically centered in top 80% of frame)
3. **Text overlays (timed):**

| Frames | Content | Style |
|--------|---------|-------|
| 0–60 | Product name (max 40 chars, wrap at 20) | White, 52pt NotoSansThai-Bold, bottom third |
| 60–150 | Price (e.g. "฿299") | Brand red (#FF4D4D), 120pt Montserrat-Bold, center |
| 150–210 | "ซื้อเลย 👆" + Shopee short URL | White, 44pt, bottom quarter |

4. **@trendyinthai watermark:** top-left, white, 36pt, all frames

### Audio
- Random pick from `assets/music/` (3 bundled CC0 tracks)
- FFmpeg trims to 7s, fade-out last 0.5s
- Audio codec: AAC 128kbps

### FFmpeg encode
```python
ffmpeg -y
  -framerate 30 -i frames/%04d.png
  -i music.mp3 -t 7 -shortest
  -vf "scale=1080:1920,format=yuv420p"
  -c:v libx264 -preset fast -crf 23
  -c:a aac -b:a 128k
  -af "afade=t=out:st=6.5:d=0.5"
  output.mp4
```

### Public API

```python
def create_clip(item: dict, output_name: str) -> Path:
    """Render 7s 1080×1920 MP4 for item. Returns output path."""
```

## Part 3: tiktok.py

Playwright-based upload (headless, same sessionid cookie pattern as `instagram.py`).

**Session:** `assets/tiktok_session.json` — sessionid cookie from browser.
**Setup:** user runs `python3 setup_tiktok.py` once to save session (same pattern as `setup_instagram.py`).

**Upload flow:**
1. Navigate to `tiktok.com/upload`
2. Set file via file chooser
3. Fill caption (product name + price + hashtags + Shopee URL)
4. Click Post

**Hashtags:** `#ShopeeThailand #แฟชั่น #ของดีราคาถูก #TikTokShop #OOTDThailand`

```python
def post_clip(video_path: Path, caption: str) -> str:
    """Upload clip to TikTok. Returns 'posted'."""
```

## Part 4: youtube.py

YouTube Data API v3 — OAuth2, free quota (10,000 units/day; upload costs 1,600 units → ~6 uploads/day free).

**Auth:** OAuth2 token stored at path from `config.YOUTUBE_TOKEN_FILE`. First run opens browser for consent.

**Video metadata:**
- Title: product name (max 100 chars)
- Description: Thai caption + price + Shopee URL + hashtags
- Tags: `["Shorts", "ShopeeThailand", "แฟชั่น", "fashion"]`
- Category: 26 (Howto & Style)
- `#Shorts` in title or description triggers Shorts placement

```python
def post_short(video_path: Path, title: str, description: str) -> str:
    """Upload to YouTube Shorts. Returns video ID."""
```

## Part 5: main.py — run_video_cycle()

```python
def run_video_cycle():
    items = pick_top_items(get_trending_fashion(), n=CLIPS_PER_DAY)
    for item in items:
        clip_path = create_clip(item, f"clip_{ts}_{i}")
        caption = build_video_caption(item)  # in content_gen.py
        post_clip(clip_path, caption)        # TikTok
        post_short(clip_path, item["itemName"][:100], caption)  # YouTube
```

`CLIPS_PER_DAY = 3` (stays within YouTube free quota).

## config.py Changes

```python
CLIPS_PER_DAY = int(os.getenv("CLIPS_PER_DAY", "3"))
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "assets/youtube_token.json")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "assets/youtube_client_secrets.json")
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| FFmpeg not found | Raise with install instructions |
| Music folder empty | Skip audio (video only) |
| TikTok session expired | Log error, skip TikTok post |
| YouTube quota exceeded | Log error, skip YouTube post |
| Frame render fails | Skip clip, continue with next item |

## Prerequisites

- FFmpeg installed (`brew install ffmpeg`)
- 3 CC0 music tracks in `assets/music/` (bundled in repo)
- Google Cloud project with YouTube Data API v3 enabled
- `assets/youtube_client_secrets.json` from Google Cloud Console
- TikTok logged in (run `setup_tiktok.py` once)

## Success Criteria

- `python3 -c "from video_gen import create_clip"` imports cleanly
- `create_clip(item, 'test')` produces valid 1080×1920 7s MP4
- TikTok upload posts clip without error
- YouTube upload returns valid video ID
- Instagram posts show clean product image only (no overlays)
