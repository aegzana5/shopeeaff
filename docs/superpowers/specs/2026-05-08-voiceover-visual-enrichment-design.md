# Voiceover & Visual Media Enrichment

**Date:** 2026-05-08
**Status:** Approved

## Goal

Add ElevenLabs TTS voiceover and external visual media (Pexels stock video + Stable Diffusion via Replicate) to existing product clips. Add four new viral clip formats. All enrichments degrade gracefully — pipeline never blocks on API failures.

## Architecture

```
tts.py          ElevenLabs API → .mp3 voiceover file
stock_media.py  Pexels API → .mp4 B-roll clip
                Replicate API (SDXL) → .jpg background image
video_gen.py    updated: existing clip functions accept optional
                  voiceover_path + bg_video_path params
viral_gen.py    4 new viral clip formats
main.py         updated: expanded clip type rotation
config.py       new API keys + feature flags
```

### Enriched product clip data flow

```
product item
  → tts.py: generate_voiceover() → assets/output/{name}_vo.mp3
  → stock_media.py: fetch_bg_video() → assets/output/{name}_bg.mp4
      fallback: generate_bg_image() → assets/output/{name}_bg.jpg
      fallback: None (existing blurred product bg)
  → video_gen.create_clip(items, voiceover_path, bg_video_path)
      compositor: bg_video frame behind product image each frame
      ffmpeg: amix voiceover (weight 1.0) + music (weight 0.4)
```

## Components

### `tts.py`

```python
generate_voiceover(item: dict, output_name: str) -> Path | None
```

- Script: `{hook_line}\n{item_name}\nลิ้งค์ด้านล่างได้เลย`
- `hook_line` = first line from `content_gen.generate_video_caption()`
- POST `/v1/text-to-speech/{ELEVENLABS_VOICE_ID}` with `model_id=eleven_multilingual_v2`
- Saves to `assets/output/{output_name}_vo.mp3`
- Returns `None` if `TTS_ENABLED=false` or API error (logs warning)

### `stock_media.py`

```python
fetch_bg_video(keywords: list[str], output_name: str) -> Path | None
generate_bg_image(item: dict, output_name: str) -> Path | None
```

**`fetch_bg_video`:**
- Keywords: top 3 English fashion terms extracted from `item["itemName"]` (simple keyword map Thai→EN)
- GET `api.pexels.com/videos/search?query=fashion+{keywords}&orientation=portrait&per_page=5`
- Download first result to `assets/output/{output_name}_bg.mp4`
- Returns `None` on 0 results or HTTP error

**`generate_bg_image`:**
- Prompt: `"fashion lifestyle {category} Bangkok aesthetic bokeh soft light"`
- Replicate SDXL (`stability-ai/sdxl`) → `assets/output/{output_name}_bg.jpg`
- Returns `None` on Replicate error

### `video_gen.py` changes

Two new optional params on all three existing clip functions:
```python
create_clip(items, output_name, voiceover_path=None, bg_video_path=None)
create_price_reveal_clip(item, output_name, voiceover_path=None, bg_video_path=None)
create_countdown_clip(items, output_name, voiceover_path=None, bg_video_path=None)
```

New helper:
```python
_composite_bg_frame(cap: cv2.VideoCapture, frame_idx: int) -> Image.Image | None
```
- Reads frame at `frame_idx` from OpenCV VideoCapture, loops if exhausted
- Resizes to CLIP_SIZE, returns PIL Image
- Frame renderer pastes bg behind product image if provided

FFmpeg audio mixing when voiceover present:
```
-filter_complex "[1:a]volume=0.4[music];[2:a]volume=1.0[vo];[music][vo]amix=inputs=2[aout]"
-map "[aout]"
```

### `viral_gen.py`

All four functions share the same output spec: 1080×1920 @ 30fps 9s MP4.
Each calls `tts.generate_voiceover()` and `stock_media.fetch_bg_video()` internally.

```python
create_before_after_clip(item: dict, output_name: str) -> Path
```
- Segment 1 (0–4s): neutral stock B-roll + text "ก่อนเจอ Shopee 😅"
- Segment 2 (4–9s): product image fullbleed + price + "หลังจากเจอ 🔥"

```python
create_pov_meme_clip(item: dict, output_name: str) -> Path
```
- Full 9s lifestyle B-roll background
- Text overlay: `"POV: เจอ {item_name[:30]} ราคา {price} ใน Shopee 🥹"`
- Voiceover reads hook

```python
create_price_shock_clip(item: dict, output_name: str) -> Path
```
- Segment 1 (0–4s): blurred product bg + "ราคาปกติ vs Shopee 🤯" (no fabricated price — just contrast framing)
- Segment 2 (4–9s): product image + "Shopee: {price}" in brand red + CTA

```python
create_beat_hook_clip(item: dict, output_name: str) -> Path
```
- Reads music file BPM via librosa (if available) else assumes 120 BPM
- Product frames cut on beat markers: each beat = new product/text reveal
- Stock B-roll background throughout

### `main.py` changes

Expanded clip type rotation:
```python
CLIP_TYPES = [
    "standard", "price_reveal", "countdown",
    "before_after", "pov_meme", "price_shock", "beat_hook",
]
```
Round-robin per run (existing `video_history` mechanism unchanged).

Enrichment wiring per run:
```python
voiceover_path = tts.generate_voiceover(item, name) if TTS_ENABLED else None
bg_video_path  = stock_media.fetch_bg_video(keywords, name) if STOCK_MEDIA_ENABLED else None
```

### `config.py` additions

```python
ELEVENLABS_API_KEY    = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID   = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
PEXELS_API_KEY        = os.getenv("PEXELS_API_KEY", "")
REPLICATE_API_TOKEN   = os.getenv("REPLICATE_API_TOKEN", "")
TTS_ENABLED           = os.getenv("TTS_ENABLED", "true").lower() == "true"
STOCK_MEDIA_ENABLED   = os.getenv("STOCK_MEDIA_ENABLED", "true").lower() == "true"
```

## Error Handling

| Failure | Behaviour |
|---------|-----------|
| ElevenLabs API error | Log warning, `voiceover_path=None`, clip renders with music only |
| Pexels 0 results | Fall through to `generate_bg_image()` |
| Replicate error | Fall through to existing blurred product background |
| Both stock sources fail | Existing blurred bg, no stock media |
| `TTS_ENABLED=false` | `generate_voiceover()` returns `None` immediately, no HTTP call |
| `STOCK_MEDIA_ENABLED=false` | Both stock functions return `None` immediately |

## Testing

| File | What it tests |
|------|---------------|
| `tests/test_tts.py` | Mock ElevenLabs HTTP; assert `.mp3` path returned; assert `None` on 4xx |
| `tests/test_stock_media.py` | Mock Pexels + Replicate; assert path returned; assert `None` on empty results |
| `tests/test_viral_gen.py` | Mock `tts` + `stock_media`; assert each format returns `.mp4` Path |
| `tests/test_video_gen.py` | Two new cases: clip with dummy `voiceover_path`; clip with dummy `bg_video_path` |

## New Dependencies

```
opencv-python-headless  # bg video frame extraction
replicate               # Stable Diffusion via Replicate API
librosa                 # BPM detection for beat_hook (optional, soft dep)
```

Add to `requirements.txt`.

## Files Changed

| File | Action |
|------|--------|
| `tts.py` | New |
| `stock_media.py` | New |
| `viral_gen.py` | New |
| `video_gen.py` | Updated — optional voiceover + bg params, `_composite_bg_frame` helper |
| `main.py` | Updated — expanded CLIP_TYPES, enrichment wiring |
| `config.py` | Updated — 6 new env vars |
| `.env.example` | Updated — new keys |
| `requirements.txt` | Updated — 3 new deps |
| `tests/test_tts.py` | New |
| `tests/test_stock_media.py` | New |
| `tests/test_viral_gen.py` | New |
| `tests/test_video_gen.py` | Updated — 2 new test cases |

## Success Criteria

- `python main.py` completes a full run with voiceover + stock B-roll without error
- Voiceover audible and not clipping over music in output MP4
- All existing clip types still work when `TTS_ENABLED=false` and `STOCK_MEDIA_ENABLED=false`
- Each viral format produces a valid 1080×1920 9s MP4
- No run fails due to Pexels/ElevenLabs/Replicate API errors — degradation path always used
