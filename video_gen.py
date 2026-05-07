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
DURATION = 9
TOTAL_FRAMES = FPS * DURATION  # 270
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


def _make_fullbleed(product_img: Image.Image) -> Image.Image:
    """Scale and center-crop product image to fill CLIP_SIZE exactly."""
    img = product_img.copy()
    scale = max(CLIP_SIZE[0] / img.width, CLIP_SIZE[1] / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - CLIP_SIZE[0]) // 2
    top = (new_h - CLIP_SIZE[1]) // 2
    return img.crop((left, top, left + CLIP_SIZE[0], top + CLIP_SIZE[1]))


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


def _build_ffmpeg_cmd(
    ffmpeg: str,
    tmp_path: Path,
    out_path: Path,
    music: "Optional[str]",
    voiceover_path: "Optional[Path]",
    duration: int = DURATION,
) -> list:
    """Build FFmpeg command. Mixes voiceover over music when both present."""
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


def create_price_reveal_clip(
    item: dict,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
    """Render 9s single-product price-reveal video: question → price flash → CTA."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()

    music_files: list = []
    if MUSIC_DIR.exists():
        music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
    music: Optional[str] = str(random.choice(music_files)) if music_files else None

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    product_img = _download_image(item["imageUrl"])
    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass
    fullbleed = _make_fullbleed(product_img)
    price = str(item.get("priceDisplay") or item.get("price", ""))
    url = item.get("affiliateUrl", "")[:50]

    font_wm = _get_font(36, thai=False)
    font_question = _get_font(64, thai=True)
    font_price = _get_font(140, thai=False)
    font_cta = _get_font(60, thai=True)
    font_url = _get_font(32, thai=False)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        for n in range(270):
            # Ken Burns zoom 1.0 → 1.1 over 270 frames
            zoom = 1.0 + (n / 270) * 0.1
            crop_w = int(CLIP_SIZE[0] / zoom)
            crop_h = int(CLIP_SIZE[1] / zoom)
            left = (CLIP_SIZE[0] - crop_w) // 2
            top = (CLIP_SIZE[1] - crop_h) // 2
            if bg_cap is not None:
                base = _composite_bg_frame(bg_cap, n) or fullbleed
            else:
                base = fullbleed
            frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)
            if bg_cap is not None:
                _paste_product(frame_img, product_img)

            draw = ImageDraw.Draw(frame_img)
            # Watermark
            draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

            if n < 90:
                # Segment 1: question
                draw.text((540, 1420), "ราคาเท่าไหร่??", font=font_question, fill=(255, 255, 255), anchor="mm")
            elif n < 180:
                # Segment 2: price flash — even frames get semi-transparent dark overlay
                if n % 2 == 0:
                    overlay = Image.new("RGBA", CLIP_SIZE, (0, 0, 0, 0))
                    ov_draw = ImageDraw.Draw(overlay)
                    ov_draw.rectangle([(0, 0), CLIP_SIZE], fill=(0, 0, 0, int(255 * 0.15)))
                    frame_rgba = frame_img.convert("RGBA")
                    frame_rgba = Image.alpha_composite(frame_rgba, overlay)
                    frame_img = frame_rgba.convert("RGB")
                    draw = ImageDraw.Draw(frame_img)
                    draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))
                draw.text((540, 1300), price, font=font_price, fill=(255, 77, 77), anchor="mm")
            else:
                # Segment 3: CTA
                draw.text((540, 1380), "ได้เลยที่ Shopee", font=font_cta, fill=(255, 255, 255), anchor="mm")
                draw.text((540, 1480), url, font=font_url, fill=(200, 200, 200), anchor="mm")

            frame_img.save(tmp_path / f"frame{n:04d}.jpg", "JPEG", quality=90)

        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def create_countdown_clip(
    items: list,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
    """Render 9s countdown clip — 5 products ranked 5→1, 1.8s each."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()

    # Pad to exactly 5 items
    if not items:
        raise ValueError("create_countdown_clip requires at least one item")
    items = (items * 5)[:5]

    music_files: list = []
    if MUSIC_DIR.exists():
        music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
    music: Optional[str] = str(random.choice(music_files)) if music_files else None

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass

    font_wm = _get_font(36, thai=False)
    font_num = _get_font(200, thai=False)
    font_name = _get_font(44, thai=True)
    font_price = _get_font(52, thai=False)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        global_frame = 0

        for rank, item in enumerate(items):
            product_img = _download_image(item["imageUrl"])
            fallback_fullbleed = _make_fullbleed(product_img)

            name = item.get("itemName", "")[:40]
            name_lines = [name[i:i + 20] for i in range(0, len(name), 20)][:3]
            price = str(item.get("priceDisplay") or item.get("price", ""))
            countdown_num = str(5 - rank)

            for f in range(54):
                # Ken Burns zoom 1.0 → 1.05
                zoom = 1.0 + (f / 54) * 0.05
                crop_w = int(CLIP_SIZE[0] / zoom)
                crop_h = int(CLIP_SIZE[1] / zoom)
                left = (CLIP_SIZE[0] - crop_w) // 2
                top = (CLIP_SIZE[1] - crop_h) // 2
                if bg_cap is not None:
                    base = _composite_bg_frame(bg_cap, global_frame) or fallback_fullbleed
                else:
                    base = fallback_fullbleed
                frame_img = base.crop((left, top, left + crop_w, top + crop_h)).resize(CLIP_SIZE, Image.LANCZOS)
                if bg_cap is not None:
                    _paste_product(frame_img, product_img)

                # Watermark
                draw = ImageDraw.Draw(frame_img)
                draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

                # Semi-transparent countdown number (top-right) via RGBA layer
                num_layer = Image.new("RGBA", CLIP_SIZE, (0, 0, 0, 0))
                num_draw = ImageDraw.Draw(num_layer)
                num_draw.text((900, 80), countdown_num, font=font_num, fill=(255, 255, 255, 180), anchor="rt")
                frame_rgba = frame_img.convert("RGBA")
                frame_rgba = Image.alpha_composite(frame_rgba, num_layer)
                frame_img = frame_rgba.convert("RGB")

                draw = ImageDraw.Draw(frame_img)
                # Re-draw watermark after composite (composite resets draw target)
                draw.text((30, 50), "@trendyinthai", font=font_wm, fill=(255, 255, 255))

                # Product name
                y = 1380
                for line in name_lines:
                    draw.text((540, y), line, font=font_name, fill=(255, 255, 255), anchor="mm")
                    y += 60

                # Price
                draw.text((540, 1480), price, font=font_price, fill=(255, 77, 77), anchor="mm")

                frame_img.save(tmp_path / f"frame{global_frame:04d}.jpg", "JPEG", quality=90)
                global_frame += 1

        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path


def create_clip(
    items: list,
    output_name: str,
    voiceover_path: "Optional[Path]" = None,
    bg_video_path: "Optional[Path]" = None,
) -> Path:
    """Render 9s 1080x1920 MP4 — 3 products, 3 seconds each, Ken Burns zoom."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_bin()

    # Pad to exactly 3 items
    if not items:
        raise ValueError("create_clip requires at least one item")
    items = (items * 3)[:3]

    music_files: list = []
    if MUSIC_DIR.exists():
        music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
    music: Optional[str] = str(random.choice(music_files)) if music_files else None

    out_path = OUTPUT_DIR / f"{output_name}.mp4"

    bg_cap = None
    if bg_video_path:
        try:
            import cv2
            bg_cap = cv2.VideoCapture(str(bg_video_path))
        except Exception:
            pass

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        global_frame = 0

        for item in items:
            product_img = _download_image(item["imageUrl"])
            seg_frames = _render_segment(
                product_img, item, frame_count=90,
                bg_cap=bg_cap, frame_offset=global_frame,
            )
            for seg_frame in seg_frames:
                seg_frame.save(tmp_path / f"frame{global_frame:04d}.jpg", "JPEG", quality=90)
                global_frame += 1

        if bg_cap:
            bg_cap.release()
        cmd = _build_ffmpeg_cmd(ffmpeg, tmp_path, out_path, music, voiceover_path)
        subprocess.run(cmd, check=True, capture_output=True)

    return out_path
