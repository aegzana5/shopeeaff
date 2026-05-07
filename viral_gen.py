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

            try:
                pov_text = f"POV: เจอ {name[:30]} ราคา {price} ใน Shopee 🥹"
                draw.text((540, 960), pov_text, font=font_pov,
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
