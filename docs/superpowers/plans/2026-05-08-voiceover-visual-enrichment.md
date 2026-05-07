# Voiceover & Visual Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ElevenLabs TTS voiceover, Pexels B-roll backgrounds, Stable Diffusion image generation, and four new viral clip formats to the fashion bot video pipeline.

**Architecture:** Three new modules (`tts.py`, `stock_media.py`, `viral_gen.py`) keep API concerns separate from rendering. `video_gen.py` gains optional `voiceover_path` and `bg_video_path` params on all three existing clip functions. `main.py` wires enrichments before clip creation and rotates across seven clip types.

**Tech Stack:** ElevenLabs API (eleven_multilingual_v2), Pexels Videos API, Replicate SDXL, OpenCV (frame extraction), librosa (optional BPM detection), existing Pillow + FFmpeg pipeline.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tts.py` | Create | ElevenLabs API → `.mp3` voiceover |
| `stock_media.py` | Create | Pexels search → `.mp4` B-roll; Replicate SDXL → `.jpg` background |
| `viral_gen.py` | Create | 4 viral clip formats using above modules + video_gen primitives |
| `video_gen.py` | Modify | Add `_composite_bg_frame`, `_build_ffmpeg_cmd`; update `_render_segment`, `create_clip`, `create_price_reveal_clip`, `create_countdown_clip` |
| `main.py` | Modify | Expand `CLIP_TYPES` to 7; wire `tts`/`stock_media` before clip creation |
| `config.py` | Modify | 6 new env vars |
| `.env.example` | Modify | Document new keys |
| `requirements.txt` | Modify | Add `opencv-python-headless`, `replicate`, `librosa` |
| `tests/test_tts.py` | Create | ElevenLabs mock tests |
| `tests/test_stock_media.py` | Create | Pexels + Replicate mock tests |
| `tests/test_viral_gen.py` | Create | Viral format tests |
| `tests/test_video_gen.py` | Modify | 2 new cases for bg_video + voiceover params |

---

## Task 1: Config, Dependencies, Env

**Files:**
- Modify: `config.py`
- Modify: `.env.example`
- Modify: `requirements.txt`

- [ ] **Step 1: Add env vars to config.py**

Append after `TIKTOK_SESSION_FILE` line in `config.py`:

```python
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
STOCK_MEDIA_ENABLED = os.getenv("STOCK_MEDIA_ENABLED", "true").lower() == "true"
```

- [ ] **Step 2: Update .env.example**

Append to `.env.example`:

```
# ElevenLabs Text-to-Speech
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Pexels Stock Video
PEXELS_API_KEY=your_pexels_key

# Replicate (Stable Diffusion)
REPLICATE_API_TOKEN=your_replicate_token

# Feature flags (set to false to disable API calls)
TTS_ENABLED=true
STOCK_MEDIA_ENABLED=true
```

- [ ] **Step 3: Add new deps to requirements.txt**

```
opencv-python-headless>=4.8.0
replicate>=0.25.0
librosa>=0.10.0
```

- [ ] **Step 4: Install and verify**

```bash
pip install opencv-python-headless>=4.8.0 replicate>=0.25.0 librosa>=0.10.0
python -c "import cv2, replicate, librosa; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add config.py .env.example requirements.txt
git commit -m "feat: add ElevenLabs, Pexels, Replicate config and deps"
```

---

## Task 2: tts.py

**Files:**
- Create: `tests/test_tts.py`
- Create: `tts.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tts.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


FAKE_ITEM = {
    "itemName": "เสื้อยืดน่ารัก Korean Style",
    "priceDisplay": "299",
    "affiliateUrl": "https://s.shopee.co.th/abc",
}


def test_generate_voiceover_returns_mp3_path(tmp_path, monkeypatch):
    monkeypatch.setattr("tts.OUTPUT_DIR", tmp_path)
    fake_resp = MagicMock()
    fake_resp.content = b"ID3\x00fake-mp3-data"
    fake_resp.raise_for_status = MagicMock()

    with patch("tts.requests.post", return_value=fake_resp), \
         patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", "test-key"), \
         patch("tts.config.ELEVENLABS_VOICE_ID", "test-voice"):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")

    assert result is not None
    assert result.suffix == ".mp3"
    assert result.exists()


def test_generate_voiceover_returns_none_when_disabled():
    with patch("tts.config.TTS_ENABLED", False):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")
    assert result is None


def test_generate_voiceover_returns_none_when_no_api_key():
    with patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", ""):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")
    assert result is None


def test_generate_voiceover_returns_none_on_api_error(tmp_path, monkeypatch):
    import requests as req_lib
    monkeypatch.setattr("tts.OUTPUT_DIR", tmp_path)
    fake_resp = MagicMock()
    fake_resp.raise_for_status.side_effect = req_lib.HTTPError("401 Unauthorized")

    with patch("tts.requests.post", return_value=fake_resp), \
         patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", "bad-key"), \
         patch("tts.config.ELEVENLABS_VOICE_ID", "test-voice"):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")

    assert result is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_tts.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'tts'`

- [ ] **Step 3: Implement tts.py**

Create `tts.py`:

```python
import logging
import requests
from pathlib import Path
import config

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("assets/output")
_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def generate_voiceover(item: dict, output_name: str) -> "Path | None":
    if not config.TTS_ENABLED or not config.ELEVENLABS_API_KEY:
        return None

    price = item.get("priceDisplay") or item.get("price", "")
    name = item["itemName"][:60]
    script = f"{name} ราคาแค่ {price} บาท\nลิ้งค์ด้านล่างได้เลย"

    url = _TTS_URL.format(voice_id=config.ELEVENLABS_VOICE_ID)
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        out_path = OUTPUT_DIR / f"{output_name}_vo.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return out_path
    except Exception as e:
        log.warning("ElevenLabs TTS failed: %s", e)
        return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_tts.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add tts.py tests/test_tts.py
git commit -m "feat: add ElevenLabs TTS voiceover module"
```

---

## Task 3: stock_media.py

**Files:**
- Create: `tests/test_stock_media.py`
- Create: `stock_media.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_stock_media.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


FAKE_ITEM = {
    "itemName": "เสื้อเดรสเกาหลี สวยมาก",
    "priceDisplay": "499",
}

PEXELS_RESPONSE = {
    "videos": [{
        "id": 1234,
        "video_files": [
            {"link": "https://cdn.pexels.com/video.mp4", "height": 1920, "width": 1080},
        ],
    }]
}


def test_fetch_bg_video_returns_mp4_path(tmp_path):
    fake_search = MagicMock()
    fake_search.json.return_value = PEXELS_RESPONSE
    fake_search.raise_for_status = MagicMock()

    fake_dl = MagicMock()
    fake_dl.iter_content.return_value = [b"fake-video-bytes"]
    fake_dl.raise_for_status = MagicMock()

    with patch("stock_media.config.STOCK_MEDIA_ENABLED", True), \
         patch("stock_media.config.PEXELS_API_KEY", "test-key"), \
         patch("stock_media.OUTPUT_DIR", tmp_path), \
         patch("stock_media.requests.get", side_effect=[fake_search, fake_dl]):
        import stock_media
        result = stock_media.fetch_bg_video(["shirt", "korean"], "test_clip")

    assert result is not None
    assert result.suffix == ".mp4"
    assert result.exists()


def test_fetch_bg_video_returns_none_on_empty_results(tmp_path):
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"videos": []}
    fake_resp.raise_for_status = MagicMock()

    with patch("stock_media.config.STOCK_MEDIA_ENABLED", True), \
         patch("stock_media.config.PEXELS_API_KEY", "test-key"), \
         patch("stock_media.OUTPUT_DIR", tmp_path), \
         patch("stock_media.requests.get", return_value=fake_resp):
        import stock_media
        result = stock_media.fetch_bg_video(["shirt"], "test_clip")

    assert result is None


def test_fetch_bg_video_returns_none_when_disabled():
    with patch("stock_media.config.STOCK_MEDIA_ENABLED", False):
        import stock_media
        result = stock_media.fetch_bg_video(["fashion"], "test_clip")
    assert result is None


def test_extract_keywords_maps_thai_shirt_to_english():
    import stock_media
    keywords = stock_media._extract_keywords("เสื้อยืดน่ารัก")
    assert any(k in ("shirt", "tshirt") for k in keywords)


def test_extract_keywords_maps_thai_korean_style():
    import stock_media
    keywords = stock_media._extract_keywords("เสื้อเกาหลี สวยมาก")
    assert "korean" in keywords


def test_extract_keywords_fallback():
    import stock_media
    keywords = stock_media._extract_keywords("สินค้าทั่วไป")
    assert keywords == ["fashion"]


def test_extract_keywords_picks_up_english_words():
    import stock_media
    keywords = stock_media._extract_keywords("Dress เดรส Korean Style")
    assert "Dress" in keywords or "dress" in keywords or "korean" in keywords
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_stock_media.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'stock_media'`

- [ ] **Step 3: Implement stock_media.py**

Create `stock_media.py`:

```python
import logging
import re
import requests
from pathlib import Path
import config

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("assets/output")

_PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

_THAI_TO_EN = {
    "เสื้อ": "shirt",
    "เสื้อยืด": "tshirt",
    "กางเกง": "pants",
    "กระโปรง": "skirt",
    "ชุด": "dress",
    "เดรส": "dress",
    "รองเท้า": "shoes",
    "กระเป๋า": "bag",
    "แจ็คเก็ต": "jacket",
    "บลาวส์": "blouse",
    "แฟชั่น": "fashion",
    "เกาหลี": "korean",
    "ญี่ปุ่น": "japanese",
    "สาว": "girl",
}


def _extract_keywords(item_name: str) -> list:
    keywords = []
    for thai, en in _THAI_TO_EN.items():
        if thai in item_name and en not in keywords:
            keywords.append(en)
    en_words = re.findall(r"[A-Za-z]{3,}", item_name)
    for w in en_words[:2]:
        if w.lower() not in keywords:
            keywords.append(w)
    return (keywords or ["fashion"])[:3]


def fetch_bg_video(keywords: list, output_name: str) -> "Path | None":
    if not config.STOCK_MEDIA_ENABLED or not config.PEXELS_API_KEY:
        return None

    query = "fashion " + " ".join(keywords[:3])
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": 5,
        "size": "medium",
    }

    try:
        resp = requests.get(_PEXELS_VIDEO_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            return None

        video_files = sorted(
            videos[0]["video_files"],
            key=lambda x: x.get("height", 0),
            reverse=True,
        )
        video_url = video_files[0]["link"]

        out_path = OUTPUT_DIR / f"{output_name}_bg.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        dl = requests.get(video_url, stream=True, timeout=60)
        dl.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in dl.iter_content(chunk_size=8192):
                f.write(chunk)
        return out_path
    except Exception as e:
        log.warning("Pexels fetch failed: %s", e)
        return None


def generate_bg_image(item: dict, output_name: str) -> "Path | None":
    if not config.STOCK_MEDIA_ENABLED or not config.REPLICATE_API_TOKEN:
        return None

    keywords = _extract_keywords(item["itemName"])
    prompt = (
        f"fashion lifestyle {' '.join(keywords)} Bangkok street aesthetic "
        "bokeh soft light vibrant colors, vertical portrait 9:16"
    )

    try:
        import replicate
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={"prompt": prompt, "width": 768, "height": 1344, "num_outputs": 1},
        )
        img_url = str(output[0])
        resp = requests.get(img_url, timeout=30)
        resp.raise_for_status()
        out_path = OUTPUT_DIR / f"{output_name}_bg.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return out_path
    except Exception as e:
        log.warning("Replicate SD failed: %s", e)
        return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_stock_media.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add stock_media.py tests/test_stock_media.py
git commit -m "feat: add Pexels stock video and Replicate SD background module"
```

---

## Task 4: video_gen.py — bg_video and voiceover support

**Files:**
- Modify: `video_gen.py`
- Modify: `tests/test_video_gen.py`

The changes add two helpers (`_composite_bg_frame`, `_build_ffmpeg_cmd`), update `_render_segment` to accept `bg_cap`/`frame_offset` params, and add `voiceover_path`/`bg_video_path` to all three public clip functions.

- [ ] **Step 1: Add new test cases to test_video_gen.py**

Open `tests/test_video_gen.py` and append these two tests. Follow the existing file's mock pattern: patch `subprocess.run` (not `video_gen.subprocess.run`), and pass a list to `create_clip`.

```python
def test_create_clip_with_voiceover_includes_audio_in_cmd(tmp_path):
    """FFmpeg cmd should include voiceover path when voiceover_path is given."""
    fake_vo = tmp_path / "vo.mp3"
    fake_vo.write_bytes(b"fake-audio")
    mock_result = MagicMock()

    with patch("video_gen._download_image", side_effect=_fake_download), \
         patch("video_gen.OUTPUT_DIR", tmp_path), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        from video_gen import create_clip
        out = create_clip([SAMPLE_ITEM], "test_vo", voiceover_path=fake_vo)

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert any(str(fake_vo) in str(c) for c in cmd), \
        "voiceover_path must appear in ffmpeg command"
    assert str(out).endswith(".mp4")


def test_create_clip_with_nonexistent_bg_video_completes(tmp_path):
    """create_clip with a bg_video_path that can't be opened falls back gracefully."""
    nonexistent_bg = tmp_path / "nonexistent_bg.mp4"
    mock_result = MagicMock()

    with patch("video_gen._download_image", side_effect=_fake_download), \
         patch("video_gen.OUTPUT_DIR", tmp_path), \
         patch("subprocess.run", return_value=mock_result):
        from video_gen import create_clip
        out = create_clip([SAMPLE_ITEM], "test_bg", bg_video_path=nonexistent_bg)

    assert str(out).endswith(".mp4")
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_video_gen.py::test_create_clip_with_voiceover_passes_audio_input tests/test_video_gen.py::test_create_clip_with_bg_video_completes -v 2>&1 | tail -10
```

Expected: both FAIL (no `voiceover_path` param yet)

- [ ] **Step 3: Add `_composite_bg_frame` helper to video_gen.py**

Insert after `_make_fullbleed` (line 132) and before `_render_segment` (line 135):

```python
def _composite_bg_frame(cap, frame_idx: int) -> "Image.Image | None":
    """Extract frame at frame_idx from an OpenCV VideoCapture, resize to CLIP_SIZE."""
    try:
        import cv2
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        pos = frame_idx % total if total > 0 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        if not ret:
            return None
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        scale = max(CLIP_SIZE[0] / img.width, CLIP_SIZE[1] / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - CLIP_SIZE[0]) // 2
        top = (new_h - CLIP_SIZE[1]) // 2
        return img.crop((left, top, left + CLIP_SIZE[0], top + CLIP_SIZE[1]))
    except Exception:
        return None
```

- [ ] **Step 4: Add `_build_ffmpeg_cmd` helper to video_gen.py**

Insert after `_composite_bg_frame`:

```python
def _build_ffmpeg_cmd(
    ffmpeg: str,
    tmp_path: Path,
    out_path: Path,
    music: "Optional[str]",
    voiceover_path: "Optional[Path]",
    duration: int = DURATION,
) -> list:
    """Build FFmpeg command for video encoding. Mixes voiceover over music when both present."""
    base = [
        ffmpeg, "-y",
        "-framerate", str(FPS),
        "-i", str(tmp_path / "frame%04d.jpg"),
    ]
    vf = f"scale={CLIP_SIZE[0]}:{CLIP_SIZE[1]},format=yuv420p"
    vc = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]

    if music and voiceover_path:
        return base + [
            "-i", str(music),
            "-i", str(voiceover_path),
            "-t", str(duration),
            "-filter_complex",
            "[1:a]volume=0.4[m];[2:a]volume=1.0[v];[m][v]amix=inputs=2:normalize=0,"
            "afade=t=out:st=8.5:d=0.5[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-vf", vf,
        ] + vc + ["-c:a", "aac", "-b:a", "128k", str(out_path)]
    elif music:
        return base + [
            "-i", str(music),
            "-t", str(duration),
            "-vf", vf,
        ] + vc + [
            "-c:a", "aac", "-b:a", "128k",
            "-af", "afade=t=out:st=8.5:d=0.5",
            "-shortest", str(out_path),
        ]
    elif voiceover_path:
        return base + [
            "-i", str(voiceover_path),
            "-t", str(duration),
            "-vf", vf,
        ] + vc + ["-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)]
    else:
        return base + [
            "-t", str(duration),
            "-vf", vf,
        ] + vc + [str(out_path)]
```

- [ ] **Step 5: Update `_render_segment` signature and body**

Replace the existing `_render_segment` function (lines 135–181) with:

```python
def _render_segment(
    product_img: Image.Image,
    item: dict,
    frame_count: int = 90,
    bg_cap=None,
    frame_offset: int = 0,
) -> list:
    """Return PIL.Image frames for one product segment (Ken Burns + text overlays).

    When bg_cap is provided, uses video frames as background and pastes product centered.
    When bg_cap is None, uses product image fullbleed as background (original behaviour).
    """
    if bg_cap is None:
        fullbleed = _make_fullbleed(product_img)

    name = item.get("itemName", "")[:40]
    price = str(item.get("priceDisplay") or item.get("price", ""))
    name_lines = [name[i:i + 20] for i in range(0, len(name), 20)][:3]

    font_handle = _get_font(36, thai=False)
    font_name = _get_font(52, thai=True)
    font_price = _get_font(100, thai=False)
    font_cta = _get_font(60, thai=True)

    frames = []
    for f in range(frame_count):
        if bg_cap is not None:
            base = _composite_bg_frame(bg_cap, frame_offset + f) or _make_fullbleed(product_img)
        else:
            base = fullbleed

        zoom_factor = 1.0 + (f / frame_count) * 0.1
        crop_w = int(CLIP_SIZE[0] / zoom_factor)
        crop_h = int(CLIP_SIZE[1] / zoom_factor)
        left = (CLIP_SIZE[0] - crop_w) // 2
        top = (CLIP_SIZE[1] - crop_h) // 2
        frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)

        if bg_cap is not None:
            _paste_product(frame_img, product_img)

        draw = ImageDraw.Draw(frame_img)
        draw.text((30, 50), "@trendyinthai", font=font_handle, fill=(255, 255, 255))

        if f < 30:
            y = 1420
            for line in name_lines:
                draw.text((540, y), line, font=font_name, fill=(255, 255, 255), anchor="mm")
                y += 70
        elif f < 70:
            draw.text((540, 1320), price, font=font_price, fill=BRAND_COLOR, anchor="mm")
        else:
            try:
                draw.text((540, 1420), "ซื้อเลย 👆", font=font_cta, fill=(255, 255, 255), anchor="mm")
            except Exception:
                draw.text((540, 1420), "ซื้อเลย", font=font_cta, fill=(255, 255, 255), anchor="mm")

        frames.append(frame_img)

    return frames
```

- [ ] **Step 6: Update `create_price_reveal_clip` signature and FFmpeg block**

Replace the function signature (line 184) with:

```python
def create_price_reveal_clip(
    item: dict,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
```

After `product_img = _download_image(item["imageUrl"])` add:

```python
    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass
```

Change `fullbleed = _make_fullbleed(product_img)` to:

```python
    fullbleed = _make_fullbleed(product_img)  # fallback when bg_cap is None
```

Inside the `for n in range(270)` loop, replace `frame_img = fullbleed.crop(...)...` with:

```python
            if bg_cap is not None:
                base = _composite_bg_frame(bg_cap, n) or fullbleed
            else:
                base = fullbleed
            frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)
            if bg_cap is not None:
                _paste_product(frame_img, product_img)
```

Before `subprocess.run(cmd, ...)` replace the entire `if music: ... else: ... subprocess.run(...)` block with:

```python
        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)
```

- [ ] **Step 7: Update `create_countdown_clip` signature and FFmpeg block**

Replace signature:

```python
def create_countdown_clip(
    items: list,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
```

After `out_path = OUTPUT_DIR / f"{output_name}.mp4"` add:

```python
    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass
```

Inside the `for rank, item in enumerate(items)` loop, replace `fullbleed = _make_fullbleed(product_img)` with:

```python
            fallback_fullbleed = _make_fullbleed(product_img)
```

Inside `for f in range(54)`, replace `frame_img = fullbleed.crop(...)...` with:

```python
                if bg_cap is not None:
                    base = _composite_bg_frame(bg_cap, global_frame) or fallback_fullbleed
                else:
                    base = fallback_fullbleed
                frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)
                if bg_cap is not None:
                    _paste_product(frame_img, product_img)
```

Replace the final `if music: ... subprocess.run(...)` block with:

```python
        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)
```

- [ ] **Step 8: Update `create_clip` signature and body**

Replace signature:

```python
def create_clip(
    items: list,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
```

After `out_path = OUTPUT_DIR / f"{output_name}.mp4"` add:

```python
    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass
```

Replace the `for seg_idx, item in enumerate(items)` loop with:

```python
        for item in items:
            product_img = _download_image(item["imageUrl"])
            seg_frames = _render_segment(
                product_img, item, frame_count=90,
                bg_cap=bg_cap, frame_offset=global_frame,
            )
            for seg_frame in seg_frames:
                seg_frame.save(tmp_path / f"frame{global_frame:04d}.jpg", "JPEG", quality=90)
                global_frame += 1
```

Replace the final `if music: ... subprocess.run(...)` block with:

```python
        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)
```

- [ ] **Step 9: Run all video_gen tests**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_video_gen.py -v
```

Expected: all pass including the 2 new cases

- [ ] **Step 10: Commit**

```bash
git add video_gen.py tests/test_video_gen.py
git commit -m "feat: add bg_video and voiceover support to video_gen clip functions"
```

---

## Task 5: viral_gen.py — 4 viral clip formats

**Files:**
- Create: `tests/test_viral_gen.py`
- Create: `viral_gen.py`

All four formats share the same output spec: 1080×1920 @ 30fps 9s MP4. Each internally calls `tts.generate_voiceover` and `stock_media.fetch_bg_video`. Rendering uses Pillow primitives imported from `video_gen`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_viral_gen.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image


FAKE_ITEM = {
    "itemName": "เสื้อยืดเกาหลี น่ารัก",
    "priceDisplay": "299",
    "imageUrl": "https://example.com/img.jpg",
    "affiliateUrl": "https://s.shopee.co.th/test",
    "price": "299",
    "itemId": "123",
}


def _fake_img():
    return Image.new("RGB", (600, 800), (200, 100, 50))


def _make_ffmpeg_side_effect():
    def _run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"fake-mp4-data")
    return _run


@pytest.mark.parametrize("fn_name", [
    "create_pov_meme_clip",
    "create_before_after_clip",
    "create_price_shock_clip",
    "create_beat_hook_clip",
])
def test_viral_clip_returns_mp4(fn_name, tmp_path):
    with patch("viral_gen._download_image", return_value=_fake_img()), \
         patch("viral_gen.tts.generate_voiceover", return_value=None), \
         patch("viral_gen.stock_media.fetch_bg_video", return_value=None), \
         patch("viral_gen.OUTPUT_DIR", tmp_path), \
         patch("viral_gen.subprocess.run", side_effect=_make_ffmpeg_side_effect()):
        import viral_gen
        fn = getattr(viral_gen, fn_name)
        result = fn(FAKE_ITEM, f"test_{fn_name}")

    assert result.suffix == ".mp4"
    assert result.exists()


def test_viral_clip_uses_voiceover_when_available(tmp_path):
    fake_vo = tmp_path / "vo.mp3"
    fake_vo.write_bytes(b"fake-audio")
    captured = []

    def fake_run(cmd, **kw):
        captured.append(cmd)
        Path(cmd[-1]).write_bytes(b"fake-mp4")

    with patch("viral_gen._download_image", return_value=_fake_img()), \
         patch("viral_gen.tts.generate_voiceover", return_value=fake_vo), \
         patch("viral_gen.stock_media.fetch_bg_video", return_value=None), \
         patch("viral_gen.OUTPUT_DIR", tmp_path), \
         patch("viral_gen.subprocess.run", side_effect=fake_run):
        import viral_gen
        viral_gen.create_pov_meme_clip(FAKE_ITEM, "test_vo")

    assert any(str(fake_vo) in str(c) for c in captured), \
        "voiceover path should appear in ffmpeg command"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_viral_gen.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'viral_gen'`

- [ ] **Step 3: Implement viral_gen.py**

Create `viral_gen.py`:

```python
"""
Four viral clip formats for TikTok/Instagram.
All produce 1080x1920 @ 30fps 9s MP4.
"""
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

import tts
import stock_media
from video_gen import (
    _download_image, _make_fullbleed, _paste_product, _get_font,
    _composite_bg_frame, _build_ffmpeg_cmd, _ffmpeg_bin,
    CLIP_SIZE, FPS, DURATION, BRAND_COLOR, MUSIC_DIR,
)

OUTPUT_DIR = Path("assets/output")


def _pick_music() -> Optional[str]:
    if MUSIC_DIR.exists():
        files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
        if files:
            return str(random.choice(files))
    return None


def _render_viral_frames(
    frames_dir: Path,
    render_fn,
    total: int = 270,
) -> None:
    """Call render_fn(frame_idx) -> Image.Image for each frame and save to frames_dir."""
    for i in range(total):
        img = render_fn(i)
        img.save(frames_dir / f"frame{i:04d}.jpg", "JPEG", quality=90)


def create_pov_meme_clip(item: dict, output_name: str) -> Path:
    """POV text + lifestyle B-roll + price CTA."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()
    music = _pick_music()

    keywords = stock_media._extract_keywords(item["itemName"])
    bg_path = stock_media.fetch_bg_video(keywords, output_name)
    vo_path = tts.generate_voiceover(item, output_name)

    product_img = _download_image(item["imageUrl"])
    fullbleed = _make_fullbleed(product_img)

    price = str(item.get("priceDisplay") or item.get("price", ""))
    name = item["itemName"][:35]

    font_wm = _get_font(36, thai=False)
    font_pov = _get_font(54, thai=True)
    font_price = _get_font(80, thai=False)
    font_cta = _get_font(52, thai=True)

    bg_cap = None
    if bg_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_path))
        except Exception:
            pass

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        def render_frame(n: int) -> Image.Image:
            if bg_cap is not None:
                base = _composite_bg_frame(bg_cap, n) or fullbleed
            else:
                base = fullbleed
            frame_img = base.copy()
            _paste_product(frame_img, product_img)
            draw = ImageDraw.Draw(frame_img)
            draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

            if n < 90:
                try:
                    draw.text((540, 260), f"POV: เจอ", font=font_pov,
                               fill=(255, 255, 255), anchor="mm")
                    draw.text((540, 330), name, font=font_pov,
                               fill=(255, 255, 0), anchor="mm")
                    draw.text((540, 400), "🥹", font=font_pov,
                               fill=(255, 255, 255), anchor="mm")
                except Exception:
                    pass
            elif n < 180:
                draw.text((540, 1300), price, font=font_price,
                           fill=BRAND_COLOR, anchor="mm")
                try:
                    draw.text((540, 1400), "บาท!! ใน Shopee", font=font_cta,
                               fill=(255, 255, 255), anchor="mm")
                except Exception:
                    pass
            else:
                try:
                    draw.text((540, 1420), "ลิ้งค์ด้านล่าง 👇", font=font_cta,
                               fill=(255, 255, 255), anchor="mm")
                except Exception:
                    pass
            return frame_img

        _render_viral_frames(tmp_path, render_frame)

        if bg_cap:
            bg_cap.release()

        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, vo_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def create_before_after_clip(item: dict, output_name: str) -> Path:
    """Segment 1: plain B-roll + 'ก่อนเจอ Shopee'. Segment 2: product + price reveal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()
    music = _pick_music()

    keywords = stock_media._extract_keywords(item["itemName"])
    bg_path = stock_media.fetch_bg_video(keywords, output_name)
    vo_path = tts.generate_voiceover(item, output_name)

    product_img = _download_image(item["imageUrl"])
    fullbleed = _make_fullbleed(product_img)

    price = str(item.get("priceDisplay") or item.get("price", ""))

    font_wm = _get_font(36, thai=False)
    font_big = _get_font(80, thai=True)
    font_price = _get_font(100, thai=False)
    font_cta = _get_font(56, thai=True)

    bg_cap = None
    if bg_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_path))
        except Exception:
            pass

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        def render_frame(n: int) -> Image.Image:
            draw_base = (
                (_composite_bg_frame(bg_cap, n) if bg_cap is not None else None)
                or fullbleed
            )
            frame_img = draw_base.copy()
            draw = ImageDraw.Draw(frame_img)
            draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

            if n < 120:
                # Segment 1: "ก่อน" — B-roll only, no product paste, dark overlay
                overlay = Image.new("RGBA", CLIP_SIZE, (0, 0, 0, 80))
                frame_rgba = frame_img.convert("RGBA")
                frame_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")
                draw = ImageDraw.Draw(frame_img)
                try:
                    draw.text((540, 960), "ก่อนเจอ Shopee 😅", font=font_big,
                               fill=(255, 255, 255), anchor="mm")
                except Exception:
                    draw.text((540, 960), "Before Shopee", font=font_big,
                               fill=(255, 255, 255), anchor="mm")
            else:
                # Segment 2: product reveal
                _paste_product(frame_img, product_img)
                draw = ImageDraw.Draw(frame_img)
                draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))
                if n < 180:
                    try:
                        draw.text((540, 260), "หลังจากเจอ 🔥", font=font_big,
                                   fill=(255, 255, 0), anchor="mm")
                    except Exception:
                        pass
                elif n < 240:
                    draw.text((540, 1300), price, font=font_price,
                               fill=BRAND_COLOR, anchor="mm")
                else:
                    try:
                        draw.text((540, 1420), "ลิ้งค์ด้านล่าง 👇", font=font_cta,
                                   fill=(255, 255, 255), anchor="mm")
                    except Exception:
                        pass
            return frame_img

        _render_viral_frames(tmp_path, render_frame)

        if bg_cap:
            bg_cap.release()

        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, vo_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def create_price_shock_clip(item: dict, output_name: str) -> Path:
    """Segment 1: 'ราคาปกติ vs Shopee' tease. Segment 2: product + Shopee price reveal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()
    music = _pick_music()

    keywords = stock_media._extract_keywords(item["itemName"])
    bg_path = stock_media.fetch_bg_video(keywords, output_name)
    vo_path = tts.generate_voiceover(item, output_name)

    product_img = _download_image(item["imageUrl"])
    fullbleed = _make_fullbleed(product_img)

    price = str(item.get("priceDisplay") or item.get("price", ""))

    font_wm = _get_font(36, thai=False)
    font_shock = _get_font(72, thai=True)
    font_price = _get_font(110, thai=False)
    font_label = _get_font(52, thai=False)
    font_cta = _get_font(52, thai=True)

    bg_cap = None
    if bg_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_path))
        except Exception:
            pass

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        def render_frame(n: int) -> Image.Image:
            base = (
                (_composite_bg_frame(bg_cap, n) if bg_cap is not None else None)
                or fullbleed
            )
            frame_img = base.copy()
            draw = ImageDraw.Draw(frame_img)
            draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

            if n < 120:
                overlay = Image.new("RGBA", CLIP_SIZE, (0, 0, 0, 100))
                frame_rgba = frame_img.convert("RGBA")
                frame_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")
                draw = ImageDraw.Draw(frame_img)
                try:
                    draw.text((540, 880), "ราคาปกติ vs Shopee", font=font_shock,
                               fill=(255, 255, 255), anchor="mm")
                    draw.text((540, 980), "🤯", font=font_shock,
                               fill=(255, 255, 255), anchor="mm")
                except Exception:
                    pass
            else:
                _paste_product(frame_img, product_img)
                draw = ImageDraw.Draw(frame_img)
                draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))
                if n < 210:
                    draw.text((540, 1270), "Shopee:", font=font_label,
                               fill=(255, 255, 255), anchor="mm")
                    draw.text((540, 1380), price, font=font_price,
                               fill=BRAND_COLOR, anchor="mm")
                else:
                    try:
                        draw.text((540, 1420), "ลิ้งค์ด้านล่าง 👇", font=font_cta,
                                   fill=(255, 255, 255), anchor="mm")
                    except Exception:
                        pass
            return frame_img

        _render_viral_frames(tmp_path, render_frame)

        if bg_cap:
            bg_cap.release()

        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, vo_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def create_beat_hook_clip(item: dict, output_name: str) -> Path:
    """Product frames cut on beat markers (default 120 BPM = 15 frames/beat)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()
    music = _pick_music()

    bpm = _get_bpm(music)
    beat_frames = max(8, int(FPS * 60 / bpm))

    keywords = stock_media._extract_keywords(item["itemName"])
    bg_path = stock_media.fetch_bg_video(keywords, output_name)
    vo_path = tts.generate_voiceover(item, output_name)

    product_img = _download_image(item["imageUrl"])
    fullbleed = _make_fullbleed(product_img)

    price = str(item.get("priceDisplay") or item.get("price", ""))
    name = item["itemName"][:30]

    font_wm = _get_font(36, thai=False)
    font_hook = _get_font(80, thai=True)
    font_price = _get_font(110, thai=False)

    BEAT_TEXTS = [name, price, "Shopee 🔥", name, price, "ลิ้งค์ด้านล่าง 👇"]

    bg_cap = None
    if bg_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_path))
        except Exception:
            pass

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        def render_frame(n: int) -> Image.Image:
            base = (
                (_composite_bg_frame(bg_cap, n) if bg_cap is not None else None)
                or fullbleed
            )
            beat_idx = (n // beat_frames) % len(BEAT_TEXTS)
            text = BEAT_TEXTS[beat_idx]

            # Pulse zoom: 1.0 → 1.08 within each beat
            beat_pos = (n % beat_frames) / beat_frames
            zoom = 1.0 + beat_pos * 0.08
            crop_w = int(CLIP_SIZE[0] / zoom)
            crop_h = int(CLIP_SIZE[1] / zoom)
            left = (CLIP_SIZE[0] - crop_w) // 2
            top = (CLIP_SIZE[1] - crop_h) // 2
            frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)
            _paste_product(frame_img, product_img)

            draw = ImageDraw.Draw(frame_img)
            draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))
            try:
                if text == price:
                    draw.text((540, 1350), text, font=font_price,
                               fill=BRAND_COLOR, anchor="mm")
                else:
                    draw.text((540, 1380), text, font=font_hook,
                               fill=(255, 255, 255), anchor="mm")
            except Exception:
                pass

            return frame_img

        _render_viral_frames(tmp_path, render_frame)

        if bg_cap:
            bg_cap.release()

        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, vo_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def _get_bpm(music_path: Optional[str]) -> float:
    if music_path is None:
        return 120.0
    try:
        import librosa
        y, sr = librosa.load(music_path, duration=9)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return float(tempo) if float(tempo) > 0 else 120.0
    except Exception:
        return 120.0
```

- [ ] **Step 4: Run viral_gen tests**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_viral_gen.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add viral_gen.py tests/test_viral_gen.py
git commit -m "feat: add 4 viral clip formats (pov, before/after, price shock, beat hook)"
```

---

## Task 6: main.py — expanded clip types + enrichment wiring

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update imports in main.py**

Replace the existing import block at top of `main.py`:

```python
import json
import logging
from datetime import datetime
from pathlib import Path

from shopee import get_trending_fashion, pick_top_items
from content_gen import generate_caption, generate_reel_script, generate_video_caption
from media_gen import create_post_image, create_reel
from instagram import post_image, post_reel
import random
from video_gen import create_clip, create_price_reveal_clip, create_countdown_clip
from viral_gen import (
    create_before_after_clip,
    create_pov_meme_clip,
    create_price_shock_clip,
    create_beat_hook_clip,
)
import tts
import stock_media
from tiktok import post_clip
from youtube import post_short
from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY
```

- [ ] **Step 2: Replace CLIP_TYPES and clip dispatch in run_video_cycle**

In `run_video_cycle`, replace:

```python
    CLIP_TYPES = ["multi", "price_reveal", "countdown"]
```

with:

```python
    CLIP_TYPES = [
        "multi", "price_reveal", "countdown",
        "before_after", "pov_meme", "price_shock", "beat_hook",
    ]
```

Replace the entire `if clip_type == "price_reveal": ... else: clip_path = create_clip(...)` block with:

```python
            clip_name = f"clip_{ts}_{i}"
            item = batch[0]

            # Enrichments for standard formats; viral formats call these internally.
            # Note: generate_bg_image returns a .jpg static image and is NOT used here —
            # the video pipeline (cv2.VideoCapture) only handles .mp4. Falls back to
            # blurred product bg when Pexels returns no result.
            keywords = stock_media._extract_keywords(item["itemName"])
            vo_path = tts.generate_voiceover(item, clip_name)
            bg_path = stock_media.fetch_bg_video(keywords, clip_name)

            if clip_type == "price_reveal":
                clip_path = create_price_reveal_clip(
                    item, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                )
            elif clip_type == "countdown":
                five_items = fresh[i * 3: i * 3 + 5]
                if len(five_items) < 5:
                    five_items = (five_items * 5)[:5]
                clip_path = create_countdown_clip(
                    five_items, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                )
            elif clip_type == "before_after":
                clip_path = create_before_after_clip(item, clip_name)
            elif clip_type == "pov_meme":
                clip_path = create_pov_meme_clip(item, clip_name)
            elif clip_type == "price_shock":
                clip_path = create_price_shock_clip(item, clip_name)
            elif clip_type == "beat_hook":
                clip_path = create_beat_hook_clip(item, clip_name)
            else:
                clip_path = create_clip(
                    batch, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                )
```

Also remove `ts = datetime.now().strftime(...)` from inside the loop since `clip_name` now replaces `f"clip_{ts}_{i}"` — keep `ts` definition at top of loop:

```python
        for i, batch in enumerate(clip_batches):
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                clip_type = random.choice(CLIP_TYPES)
                clip_name = f"clip_{ts}_{i}"
                item = batch[0]
                # ... enrichments and dispatch ...
```

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all tests pass

- [ ] **Step 4: Smoke test (dry run with APIs disabled)**

```bash
cd /Users/aegisen/fashion-bot && TTS_ENABLED=false STOCK_MEDIA_ENABLED=false python -c "
import main
print('Imports OK')
"
```

Expected: `Imports OK` (no errors on import)

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: wire voiceover + stock media enrichments, add 4 viral clip types to rotation"
```

---

## Final Verification

- [ ] **Run full test suite one last time**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/ -v
```

Expected: all tests pass, no import errors

- [ ] **Verify feature flags disable all external calls**

```bash
cd /Users/aegisen/fashion-bot && python -c "
import config
config.TTS_ENABLED = False
config.STOCK_MEDIA_ENABLED = False
import tts, stock_media
item = {'itemName': 'test', 'priceDisplay': '99'}
assert tts.generate_voiceover(item, 'x') is None
assert stock_media.fetch_bg_video(['fashion'], 'x') is None
assert stock_media.generate_bg_image(item, 'x') is None
print('Feature flags OK — no API calls made')
"
```

Expected: `Feature flags OK — no API calls made`
