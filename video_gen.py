"""
Generate 7s 1080x1920 product showcase clips for TikTok/YouTube Shorts.
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
FFMPEG_DEFAULT = "/opt/homebrew/bin/ffmpeg"


def _ffmpeg_bin() -> str:
    for candidate in [FFMPEG_DEFAULT, "/usr/local/bin/ffmpeg", "ffmpeg"]:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    return FFMPEG_DEFAULT


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
    """Scale product image to fill 1080x1920, blur, darken."""
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

    draw.text(
        (30, 50), "@trendyinthai",
        font=_get_font(36, thai=False),
        fill=(255, 255, 255),
    )

    if frame_idx < 60:
        lines = [name[i:i + 20] for i in range(0, len(name), 20)]
        y = 1420
        for line in lines[:3]:
            draw.text((540, y), line, font=_get_font(52), fill=(255, 255, 255), anchor="mm")
            y += 70
    elif frame_idx < 150:
        draw.text(
            (540, 1300), price,
            font=_get_font(120, thai=False),
            fill=BRAND_COLOR,
            anchor="mm",
        )
    else:
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
    """Render 7s 1080x1920 MP4 for item. Returns output path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()

    product_img = _download_image(item["imageUrl"])
    bg = _make_background(product_img)
    base_canvas = bg.copy()
    _paste_product(base_canvas, product_img)

    music_files: list = []
    if MUSIC_DIR.exists():
        music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
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
