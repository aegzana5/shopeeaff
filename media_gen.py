import os
import re
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

OUTPUT_DIR = Path("assets/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "assets/fonts/NotoSansThai-Bold.ttf"
FONT_PATH_EN = "assets/fonts/Montserrat-Bold.ttf"

IG_SIZE = (1080, 1080)
REEL_SIZE = (1080, 1920)

BRAND_COLOR = (255, 77, 77)     # red accent
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (30, 30, 30)
OVERLAY_ALPHA = 180


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


def create_post_image(item: dict, affiliate_url: str, output_name: str) -> Path:
    """Create 1080x1080 image post with product photo + branding."""
    product_img = _download_image(item["imageUrl"])
    canvas = Image.new("RGB", IG_SIZE, BG_COLOR)

    # Product image fills top 75%
    product_img = product_img.resize((1080, 810))
    canvas.paste(product_img, (0, 0))

    # Bottom info bar
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 810), (1080, 1080)], fill=(20, 20, 20))

    # Brand strip at top
    draw.rectangle([(0, 0), (1080, 60)], fill=BRAND_COLOR)
    font_brand = _get_font(32, thai=False)
    draw.text((20, 12), "@trendyinthai", font=font_brand, fill=(255, 255, 255))
    draw.text((800, 12), "Shopee TH 🛍️", font=font_brand, fill=(255, 255, 255))

    # Product name (truncated)
    name = item["itemName"][:50]
    font_name = _get_font(36)
    draw.text((30, 830), name, font=font_name, fill=(255, 255, 255))

    # Price — accept both raw int (Shopee cents) and formatted string (Lazada)
    price = item.get("priceDisplay") or item.get("priceMin") or item.get("price", "")
    if isinstance(price, (int, float)) and price > 1000:
        price_display = f"฿{float(price)/100000:.0f}"
    else:
        price_display = str(price) if price else ""
    font_price = _get_font(52, thai=False)
    draw.text((30, 900), price_display, font=font_price, fill=BRAND_COLOR)

    # Rating
    rating = item.get("ratingStar", "")
    if rating:
        draw.text((30, 980), f"⭐ {rating}", font=_get_font(34, thai=False), fill=(200, 200, 200))

    # Shopee logo text
    draw.text((800, 900), "ซื้อได้ที่\nลิ้งค์ในไบโอ", font=_get_font(34), fill=(255, 200, 0))

    out_path = OUTPUT_DIR / f"{output_name}.jpg"
    canvas.save(out_path, "JPEG", quality=95)
    return out_path


def create_reel(items: list[dict], script: dict, output_name: str) -> Path:
    """Create 5-second MP4 reel from product images with text overlays."""
    frames_dir = OUTPUT_DIR / f"{output_name}_frames"
    frames_dir.mkdir(exist_ok=True)

    # Build 3 frames (product images with overlay text)
    texts = [
        script.get("HOOK", "เทรนด์มาแรง! 🔥"),
        script.get("HIGHLIGHT", "ราคาดีมาก ✨"),
        script.get("CTA", "ลิ้งค์ในไบโอ 👆"),
    ]

    for i, item in enumerate(items[:3]):
        img = _download_image(item["imageUrl"]).resize(REEL_SIZE)
        draw = ImageDraw.Draw(img)

        # Dark overlay for text
        overlay = Image.new("RGBA", REEL_SIZE, (0, 0, 0, OVERLAY_ALPHA))
        img.paste(Image.new("RGB", (1080, 200), (0, 0, 0)), (0, REEL_SIZE[1] - 250))

        draw.text(
            (540, REEL_SIZE[1] - 180),
            texts[i],
            font=_get_font(64),
            fill=(255, 255, 255),
            anchor="mm",
        )
        draw.text(
            (540, 80),
            "@trendyinthai",
            font=_get_font(40, thai=False),
            fill=BRAND_COLOR,
            anchor="mm",
        )
        img.save(frames_dir / f"frame_{i:03d}.jpg", "JPEG", quality=90)

    # FFmpeg: each frame ~1.5s → ~4.5s total + 0.5s hold
    frame_pattern = str(frames_dir / "frame_%03d.jpg")
    out_path = OUTPUT_DIR / f"{output_name}.mp4"
    ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", "1/1.67",
        "-i", frame_pattern,
        "-vf", f"scale={REEL_SIZE[0]}:{REEL_SIZE[1]},fps=30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-t", "5",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
