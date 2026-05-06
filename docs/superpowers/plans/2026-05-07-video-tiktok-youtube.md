# Video Generation + TikTok/YouTube Shorts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate 7s product showcase clips from Shopee items, post to TikTok and YouTube Shorts, and simplify Instagram posts to clean product-only images.

**Architecture:** Pillow renders 210 frames (30fps×7s) with blurred background + centered product + timed text overlays; FFmpeg muxes frames + CC0 music into 1080×1920 MP4. TikTok uploaded via Playwright (same cookie pattern as instagram.py). YouTube uploaded via Data API v3. Instagram posts simplified to center-cropped product photo, no overlays.

**Tech Stack:** Python 3.9, Pillow, FFmpeg (`/opt/homebrew/bin/ffmpeg`), Playwright, google-api-python-client, pytest

**Prerequisites:** `brew install ffmpeg` (already available at `/opt/homebrew/bin/ffmpeg`)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `video_gen.py` | Create | Frame rendering + FFmpeg encode → MP4 |
| `tiktok.py` | Create | Playwright upload to TikTok |
| `setup_tiktok.py` | Create | One-time TikTok browser session setup |
| `youtube.py` | Create | YouTube Data API v3 upload |
| `media_gen.py` | Modify | Simplify `create_post_image` to center-crop only |
| `main.py` | Modify | Add `run_video_cycle()` |
| `config.py` | Modify | Add `CLIPS_PER_DAY`, YouTube paths |
| `requirements.txt` | Modify | Add google-api-python-client, google-auth-oauthlib |
| `tests/test_video_gen.py` | Create | Unit tests for video_gen.py |
| `tests/test_media_gen.py` | Create | Unit tests for simplified create_post_image |
| `assets/music/` | Create | Directory + 3 CC0 MP3 tracks |

---

## Task 0: Setup — Music, Requirements, Config

**Files:**
- Modify: `requirements.txt`
- Modify: `config.py`
- Create: `assets/music/` (directory + placeholder instructions)

- [ ] **Step 1: Add dependencies to requirements.txt**

Append to `/Users/aegisen/fashion-bot/requirements.txt`:

```
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
```

- [ ] **Step 2: Install new dependencies**

```bash
pip3 install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Expected: no errors.

- [ ] **Step 3: Create music directory and download 3 CC0 tracks**

```bash
mkdir -p /Users/aegisen/fashion-bot/assets/music
```

Then download 3 free CC0 tracks from Pixabay (run in browser or curl). Save as:
- `assets/music/track1.mp3`
- `assets/music/track2.mp3`
- `assets/music/track3.mp3`

Suggested tracks (download manually from pixabay.com/music, search "fashion upbeat"):
- Any 3 tracks tagged CC0, duration ≥10s.

> Note: `video_gen.py` works without music if folder is empty — audio is optional.

- [ ] **Step 4: Add config entries**

In `config.py`, add after `IMAGE_POSTS_PER_DAY`:

```python
CLIPS_PER_DAY = int(os.getenv("CLIPS_PER_DAY", "3"))
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "assets/youtube_token.json")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "assets/youtube_client_secrets.json")
TIKTOK_SESSION_FILE = os.getenv("TIKTOK_SESSION_FILE", "assets/tiktok_session.json")
```

- [ ] **Step 5: Commit**

```bash
cd /Users/aegisen/fashion-bot
git add requirements.txt config.py
git commit -m "chore: add video gen deps and config"
```

---

## Task 1: Simplify Instagram `create_post_image`

**Files:**
- Modify: `media_gen.py`
- Create: `tests/test_media_gen.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_media_gen.py`:

```python
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import pytest


def _fake_download(url: str) -> Image.Image:
    return Image.new("RGB", (800, 600), color=(200, 150, 100))


def test_create_post_image_is_1080x1080(tmp_path):
    with patch("media_gen._download_image", side_effect=_fake_download), \
         patch("media_gen.OUTPUT_DIR", tmp_path):
        from media_gen import create_post_image
        item = {
            "itemName": "Test Product",
            "imageUrl": "https://example.com/img.jpg",
            "priceDisplay": "฿299",
            "ratingStar": 4.8,
        }
        out = create_post_image(item, "https://example.com/aff", "test_out")
        img = Image.open(out)
        assert img.size == (1080, 1080)


def test_create_post_image_no_text_overlay(tmp_path):
    """Output is clean product image — no brand strip artifacts at top."""
    with patch("media_gen._download_image", side_effect=_fake_download), \
         patch("media_gen.OUTPUT_DIR", tmp_path):
        from media_gen import create_post_image
        item = {
            "itemName": "Test Product",
            "imageUrl": "https://example.com/img.jpg",
            "priceDisplay": "฿299",
            "ratingStar": 4.8,
        }
        out = create_post_image(item, "https://example.com/aff", "test_out2")
        img = Image.open(out)
        # Top-left pixel should NOT be brand red (255, 77, 77)
        r, g, b = img.getpixel((0, 0))
        assert not (r > 200 and g < 100 and b < 100), "Brand strip still present"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/aegisen/fashion-bot && python3 -m pytest tests/test_media_gen.py -v
```

Expected: `FAILED` — brand strip assertion triggers.

- [ ] **Step 3: Rewrite `create_post_image` in `media_gen.py`**

Replace the entire `create_post_image` function (lines 39–82) with:

```python
def create_post_image(item: dict, affiliate_url: str, output_name: str) -> Path:
    """Download product image, center-crop to 1080×1080, save as JPEG."""
    product_img = _download_image(item["imageUrl"])

    # Center-crop to square
    w, h = product_img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    product_img = product_img.crop((left, top, left + side, top + side))

    product_img = product_img.resize(IG_SIZE, Image.LANCZOS)

    out_path = OUTPUT_DIR / f"{output_name}.jpg"
    product_img.save(out_path, "JPEG", quality=95)
    return out_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python3 -m pytest tests/test_media_gen.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add media_gen.py tests/test_media_gen.py
git commit -m "feat: simplify IG posts to clean center-crop product image"
```

---

## Task 2: `video_gen.py` — Frame Rendering + FFmpeg Encode

**Files:**
- Create: `video_gen.py`
- Create: `tests/test_video_gen.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_video_gen.py`:

```python
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from PIL import Image
import pytest


SAMPLE_ITEM = {
    "itemId": "123",
    "itemName": "เสื้อยืดสีขาว ผู้หญิง สไตล์เกาหลี",
    "priceDisplay": "฿299",
    "price": "299",
    "imageUrl": "https://example.com/img.jpg",
    "affiliateUrl": "https://shope.ee/abc123",
    "shopName": "Shop A",
    "ratingStar": 4.8,
    "sales": 500,
}


def _fake_download(url: str) -> Image.Image:
    return Image.new("RGB", (800, 800), color=(180, 120, 80))


def test_make_background_fills_clip_size():
    from video_gen import _make_background, CLIP_SIZE
    product = Image.new("RGB", (500, 500), color=(100, 200, 50))
    bg = _make_background(product)
    assert bg.size == CLIP_SIZE


def test_render_frame_returns_clip_size():
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame = _render_frame(base, 0, SAMPLE_ITEM)
    assert frame.size == CLIP_SIZE


def test_render_frame_phase_name(tmp_path):
    """Frame 0 renders product name phase."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    # Should not raise
    frame = _render_frame(base, 0, SAMPLE_ITEM)
    assert frame is not None


def test_render_frame_phase_price():
    """Frame 90 renders price phase."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame = _render_frame(base, 90, SAMPLE_ITEM)
    assert frame is not None


def test_render_frame_phase_cta():
    """Frame 180 renders CTA phase."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame = _render_frame(base, 180, SAMPLE_ITEM)
    assert frame is not None


def test_create_clip_calls_ffmpeg(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("video_gen._download_image", side_effect=_fake_download), \
         patch("video_gen.OUTPUT_DIR", tmp_path), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        from video_gen import create_clip
        out = create_clip(SAMPLE_ITEM, "test_clip")
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "/opt/homebrew/bin/ffmpeg" in cmd or "ffmpeg" in cmd[0]
        assert str(out).endswith(".mp4")


def test_create_clip_output_path(tmp_path):
    mock_result = MagicMock()
    with patch("video_gen._download_image", side_effect=_fake_download), \
         patch("video_gen.OUTPUT_DIR", tmp_path), \
         patch("subprocess.run", return_value=mock_result):
        from video_gen import create_clip
        out = create_clip(SAMPLE_ITEM, "my_clip")
        assert out == tmp_path / "my_clip.mp4"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python3 -m pytest tests/test_video_gen.py -v
```

Expected: `ERROR` — `video_gen` module not found.

- [ ] **Step 3: Create `video_gen.py`**

Create `/Users/aegisen/fashion-bot/video_gen.py`:

```python
"""
Generate 7s 1080×1920 product showcase clips for TikTok/YouTube Shorts.
Pillow renders frames, FFmpeg encodes to MP4.
"""
import random
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path("assets/output")
MUSIC_DIR = Path("assets/music")
FONT_PATH = "assets/fonts/NotoSansThai-Bold.ttf"
FONT_PATH_EN = "assets/fonts/Montserrat-Bold.ttf"

CLIP_SIZE = (1080, 1920)
FPS = 30
DURATION = 7
TOTAL_FRAMES = FPS * DURATION  # 210
BRAND_COLOR = (255, 77, 77)
FFMPEG = "/opt/homebrew/bin/ffmpeg"


def _ffmpeg_bin() -> str:
    for candidate in [FFMPEG, "/usr/local/bin/ffmpeg", "ffmpeg"]:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise RuntimeError("FFmpeg not found. Install: brew install ffmpeg")


def _download_image(url: str) -> Image.Image:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


def _get_font(size: int, thai: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_PATH if thai else FONT_PATH_EN
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _make_background(product_img: Image.Image) -> Image.Image:
    """Scale product image to fill 1080×1920, blur, darken."""
    bg = product_img.copy()
    scale = max(CLIP_SIZE[0] / bg.width, CLIP_SIZE[1] / bg.height)
    new_w = int(bg.width * scale)
    new_h = int(bg.height * scale)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - CLIP_SIZE[0]) // 2
    top = (new_h - CLIP_SIZE[1]) // 2
    bg = bg.crop((left, top, left + CLIP_SIZE[0], top + CLIP_SIZE[1]))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    dark = Image.new("RGB", CLIP_SIZE, (0, 0, 0))
    return Image.blend(bg, dark, alpha=0.35)


def _paste_product(canvas: Image.Image, product_img: Image.Image) -> None:
    """Paste product image centered in top 80% of canvas."""
    max_w, max_h = 1000, 1400
    scale = min(max_w / product_img.width, max_h / product_img.height)
    w = int(product_img.width * scale)
    h = int(product_img.height * scale)
    resized = product_img.resize((w, h), Image.LANCZOS)
    x = (CLIP_SIZE[0] - w) // 2
    center_zone = int(CLIP_SIZE[1] * 0.78)
    y = (center_zone - h) // 2
    canvas.paste(resized, (x, y))


def _render_frame(base_canvas: Image.Image, frame_idx: int, item: dict) -> Image.Image:
    """Render one frame with timed text overlays onto a copy of base_canvas."""
    frame = base_canvas.copy()
    draw = ImageDraw.Draw(frame)

    name = item["itemName"][:40]
    price = str(item.get("priceDisplay") or item.get("price", ""))
    url = item.get("affiliateUrl", "")[:50]

    # Watermark — always visible
    draw.text(
        (30, 50), "@trendyinthai",
        font=_get_font(36, thai=False),
        fill=(255, 255, 255),
    )

    if frame_idx < 60:
        # Phase 1: product name
        lines = [name[i:i+20] for i in range(0, len(name), 20)]
        y = 1420
        for line in lines[:3]:
            draw.text((540, y), line, font=_get_font(52), fill=(255, 255, 255), anchor="mm")
            y += 70

    elif frame_idx < 150:
        # Phase 2: price
        draw.text(
            (540, 1300), price,
            font=_get_font(120, thai=False),
            fill=BRAND_COLOR,
            anchor="mm",
        )

    else:
        # Phase 3: CTA + URL
        draw.text(
            (540, 1380), "ซื้อเลย 👆",
            font=_get_font(60),
            fill=(255, 255, 255),
            anchor="mm",
        )
        draw.text(
            (540, 1480), url,
            font=_get_font(34, thai=False),
            fill=(200, 200, 200),
            anchor="mm",
        )

    return frame


def create_clip(item: dict, output_name: str) -> Path:
    """Render 7s 1080×1920 MP4 for item. Returns output path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()

    product_img = _download_image(item["imageUrl"])
    bg = _make_background(product_img)
    base_canvas = bg.copy()
    _paste_product(base_canvas, product_img)

    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a")) \
        if MUSIC_DIR.exists() else []
    music: Optional[str] = str(random.choice(music_files)) if music_files else None

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        frames_dir = Path(tmp)
        for i in range(TOTAL_FRAMES):
            frame = _render_frame(base_canvas, i, item)
            frame.save(frames_dir / f"{i:04d}.jpg", "JPEG", quality=85)

        if music:
            cmd = [
                ffmpeg, "-y",
                "-framerate", str(FPS),
                "-i", str(frames_dir / "%04d.jpg"),
                "-i", music,
                "-t", str(DURATION),
                "-vf", f"scale={CLIP_SIZE[0]}:{CLIP_SIZE[1]},format=yuv420p",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-af", "afade=t=out:st=6.5:d=0.5",
                "-shortest",
                str(out_path),
            ]
        else:
            cmd = [
                ffmpeg, "-y",
                "-framerate", str(FPS),
                "-i", str(frames_dir / "%04d.jpg"),
                "-t", str(DURATION),
                "-vf", f"scale={CLIP_SIZE[0]}:{CLIP_SIZE[1]},format=yuv420p",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                str(out_path),
            ]

        subprocess.run(cmd, check=True, capture_output=True)

    return out_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python3 -m pytest tests/test_video_gen.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Smoke test with real item (no TikTok/YouTube yet)**

```bash
cd /Users/aegisen/fashion-bot && python3 - <<'EOF'
from shopee import get_trending_fashion, pick_top_items
from video_gen import create_clip
items = get_trending_fashion()
item = pick_top_items(items, 1)[0]
print("Item:", item["itemName"][:50])
out = create_clip(item, "smoke_test")
print("Clip:", out, "exists:", out.exists())
EOF
```

Expected: prints clip path, file exists, size > 100KB.

- [ ] **Step 6: Commit**

```bash
git add video_gen.py tests/test_video_gen.py
git commit -m "feat: add video_gen.py — Pillow frames + FFmpeg 7s clips"
```

---

## Task 3: `tiktok.py` + `setup_tiktok.py`

**Files:**
- Create: `tiktok.py`
- Create: `setup_tiktok.py`

- [ ] **Step 1: Create `setup_tiktok.py`**

Create `/Users/aegisen/fashion-bot/setup_tiktok.py`:

```python
"""
One-time setup: open browser, log into TikTok, save session.
Run: python3 setup_tiktok.py
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path("assets/tiktok_session.json")
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)


def main():
    print("Opening browser for TikTok login...")
    print("1. Log into TikTok in the browser window")
    print("2. Once you see the TikTok home feed, come back here and press Enter")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")

        input("\nPress Enter after you have logged in and can see the TikTok feed...")

        cookies = ctx.cookies()
        session_data = {"cookies": cookies}
        SESSION_FILE.write_text(json.dumps(session_data, indent=2))
        print(f"Session saved to {SESSION_FILE}")
        browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `tiktok.py`**

Create `/Users/aegisen/fashion-bot/tiktok.py`:

```python
"""
TikTok clip upload via Playwright.
Session loaded from assets/tiktok_session.json.
"""
import json
import time
from pathlib import Path

from config import TIKTOK_SESSION_FILE

SESSION_FILE = Path(TIKTOK_SESSION_FILE)

HASHTAGS = "#ShopeeThailand #แฟชั่น #ของดีราคาถูก #OOTDThailand #ShopeeTH"


def _load_cookies():
    if not SESSION_FILE.exists():
        raise RuntimeError(
            "No TikTok session found. Run: python3 setup_tiktok.py"
        )
    data = json.loads(SESSION_FILE.read_text())
    return data.get("cookies", [])


def post_clip(video_path: Path, caption: str) -> str:
    """Upload clip to TikTok. Returns 'posted' on success."""
    from playwright.sync_api import sync_playwright

    video_path = Path(video_path).absolute()
    cookies = _load_cookies()

    with sync_playwright() as p:
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
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        try:
            page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            if "login" in page.url:
                browser.close()
                raise RuntimeError(
                    "TikTok session expired. Run: python3 setup_tiktok.py"
                )

            # Upload file
            with page.expect_file_chooser(timeout=15000) as fc_info:
                for sel in ['input[type="file"]', '[class*="upload"]']:
                    lc = page.locator(sel)
                    if lc.count() > 0:
                        lc.first.click()
                        break
            fc_info.value.set_files(str(video_path))
            time.sleep(5)

            # Fill caption
            full_caption = f"{caption}\n\n{HASHTAGS}"
            for sel in ['div[contenteditable="true"]', 'textarea']:
                lc = page.locator(sel)
                if lc.count() > 0:
                    lc.first.click()
                    lc.first.fill(full_caption)
                    break
            time.sleep(1)

            # Post
            for txt in ["Post", "投稿", "โพสต์"]:
                lc = page.locator(f'button:has-text("{txt}")')
                if lc.count() > 0:
                    lc.last.click()
                    break
            time.sleep(10)

            browser.close()
            return "posted"
        except Exception as e:
            browser.close()
            raise RuntimeError(f"TikTok post failed: {e}") from e
```

- [ ] **Step 3: Verify imports clean**

```bash
cd /Users/aegisen/fashion-bot && python3 -c "from tiktok import post_clip; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add tiktok.py setup_tiktok.py
git commit -m "feat: add TikTok Playwright upload"
```

---

## Task 4: `youtube.py`

**Files:**
- Create: `youtube.py`

**Prerequisites:** Google Cloud project with YouTube Data API v3 enabled. Download OAuth2 credentials JSON and save as `assets/youtube_client_secrets.json`.

- [ ] **Step 1: Create `youtube.py`**

Create `/Users/aegisen/fashion-bot/youtube.py`:

```python
"""
YouTube Shorts upload via YouTube Data API v3.
OAuth2 token stored at config.YOUTUBE_TOKEN_FILE.
First run opens browser for Google consent.
"""
import logging
from pathlib import Path

from config import YOUTUBE_TOKEN_FILE, YOUTUBE_CLIENT_SECRETS

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SHORTS_HASHTAG = "#Shorts"


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = Path(YOUTUBE_TOKEN_FILE)
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS)

    if not secrets_path.exists():
        raise RuntimeError(
            f"YouTube client secrets not found at {secrets_path}. "
            "Download from Google Cloud Console → APIs & Services → Credentials."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def post_short(video_path: Path, title: str, description: str) -> str:
    """Upload video as YouTube Short. Returns video ID."""
    from googleapiclient.http import MediaFileUpload

    youtube = _get_service()
    video_path = Path(video_path).absolute()

    short_title = f"{title[:95]} {SHORTS_HASHTAG}" if len(title) <= 95 else f"{title[:94]} {SHORTS_HASHTAG}"

    body = {
        "snippet": {
            "title": short_title,
            "description": f"{description}\n\n{SHORTS_HASHTAG}",
            "tags": ["Shorts", "ShopeeThailand", "แฟชั่น", "fashion", "OOTDThailand"],
            "categoryId": "26",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    log.info("YouTube Short uploaded: https://youtube.com/shorts/%s", video_id)
    return video_id
```

- [ ] **Step 2: Verify imports clean**

```bash
cd /Users/aegisen/fashion-bot && python3 -c "from youtube import post_short; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add youtube.py
git commit -m "feat: add YouTube Shorts upload via Data API v3"
```

---

## Task 5: `main.py` — `run_video_cycle()`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add `run_video_cycle` to `main.py`**

Add these imports at the top of `main.py` (after existing imports):

```python
from video_gen import create_clip
from tiktok import post_clip
from youtube import post_short
from config import CLIPS_PER_DAY
```

Add `run_video_cycle` function after `run_post_cycle`:

```python
def run_video_cycle():
    log.info("Starting video cycle")

    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee feed")
        return

    clip_items = pick_top_items(items, n=CLIPS_PER_DAY + 5)[POSTS_PER_DAY:]
    clip_items = clip_items[:CLIPS_PER_DAY]

    posted = 0
    for i, item in enumerate(clip_items):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_path = create_clip(item, f"clip_{ts}_{i}")
            caption_data = generate_caption(item, post_type="reel")
            caption = caption_data["caption"]
            title = item["itemName"][:100]

            try:
                post_clip(clip_path, caption)
                log.info(f"TikTok posted: {item['itemName'][:40]}")
            except Exception as e:
                log.error(f"TikTok post {i} failed: {e}")

            try:
                video_id = post_short(clip_path, title, caption)
                log.info(f"YouTube Short posted: {video_id}")
            except Exception as e:
                log.error(f"YouTube post {i} failed: {e}")

            posted += 1
        except Exception as e:
            log.error(f"Video clip {i} failed: {e}")

    log.info(f"Video cycle done: {posted}/{CLIPS_PER_DAY} clips")
```

Update `if __name__ == "__main__":` block:

```python
if __name__ == "__main__":
    run_post_cycle()
    run_video_cycle()
```

- [ ] **Step 2: Verify imports clean**

```bash
cd /Users/aegisen/fashion-bot && python3 -c "from main import run_video_cycle; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add run_video_cycle to main.py"
```

---

## Task 6: End-to-End Smoke Test

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/aegisen/fashion-bot && python3 -m pytest tests/ -v
```

Expected: all tests PASS (test_shopee, test_media_gen, test_video_gen).

- [ ] **Step 2: Generate one real clip without posting**

```bash
cd /Users/aegisen/fashion-bot && python3 - <<'EOF'
from shopee import get_trending_fashion, pick_top_items
from video_gen import create_clip
items = get_trending_fashion()
item = pick_top_items(items, 1)[0]
print("Item:", item["itemName"][:50])
print("Price:", item["priceDisplay"])
out = create_clip(item, "final_smoke_test")
import os
size_kb = os.path.getsize(out) // 1024
print(f"Clip: {out} ({size_kb} KB)")
assert size_kb > 100, f"Clip too small: {size_kb}KB"
print("OK")
EOF
```

Expected: clip path printed, size > 100KB, "OK".

- [ ] **Step 3: Setup TikTok session (one-time interactive)**

```bash
python3 setup_tiktok.py
```

Log in via browser, press Enter when done.

- [ ] **Step 4: Setup YouTube OAuth (one-time interactive)**

Ensure `assets/youtube_client_secrets.json` exists, then:

```bash
cd /Users/aegisen/fashion-bot && python3 - <<'EOF'
from youtube import _get_service
svc = _get_service()
print("YouTube auth OK")
EOF
```

Browser opens for Google consent on first run. Token saved to `assets/youtube_token.json`.

- [ ] **Step 5: Run full video cycle**

```bash
cd /Users/aegisen/fashion-bot && python3 -c "
from main import run_video_cycle
run_video_cycle()
"
```

Expected: logs show clips generated + posted to TikTok + YouTube.

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "chore: verified video + TikTok + YouTube Shorts end-to-end"
```
