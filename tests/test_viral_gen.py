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
