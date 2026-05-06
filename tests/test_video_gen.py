import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
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


def test_paste_product_centers_on_canvas():
    from video_gen import _paste_product, CLIP_SIZE
    canvas = Image.new("RGB", CLIP_SIZE, color=(0, 0, 0))
    product = Image.new("RGB", (400, 400), color=(255, 255, 255))
    _paste_product(canvas, product)
    # After pasting white product, canvas should have non-black pixels in center
    cx, cy = CLIP_SIZE[0] // 2, int(CLIP_SIZE[1] * 0.39)
    r, g, b = canvas.getpixel((cx, cy))
    assert r > 200 and g > 200 and b > 200, "Product not pasted at center"


def test_render_frame_returns_clip_size():
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame = _render_frame(base, 0, SAMPLE_ITEM)
    assert frame.size == CLIP_SIZE


def test_render_frame_phase_name_differs_from_phase_price():
    """Name phase (frame 0) and price phase (frame 90) produce different pixels."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame_name = _render_frame(base, 0, SAMPLE_ITEM)
    frame_price = _render_frame(base, 90, SAMPLE_ITEM)
    assert frame_name.tobytes() != frame_price.tobytes()


def test_render_frame_phase_cta_differs_from_phase_price():
    """CTA phase (frame 180) differs from price phase (frame 90)."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame_price = _render_frame(base, 90, SAMPLE_ITEM)
    frame_cta = _render_frame(base, 180, SAMPLE_ITEM)
    assert frame_price.tobytes() != frame_cta.tobytes()


def test_render_frame_differs_from_base():
    """Rendered frame has text drawn on it — differs from unmodified base."""
    from video_gen import _render_frame, CLIP_SIZE
    base = Image.new("RGB", CLIP_SIZE, color=(50, 50, 50))
    frame = _render_frame(base, 0, SAMPLE_ITEM)
    assert frame.tobytes() != base.tobytes()


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
        assert any("ffmpeg" in str(c) for c in cmd)
        assert str(out).endswith(".mp4")


def test_create_clip_output_path(tmp_path):
    mock_result = MagicMock()
    with patch("video_gen._download_image", side_effect=_fake_download), \
         patch("video_gen.OUTPUT_DIR", tmp_path), \
         patch("subprocess.run", return_value=mock_result):
        from video_gen import create_clip
        out = create_clip(SAMPLE_ITEM, "my_clip")
        assert out == tmp_path / "my_clip.mp4"
