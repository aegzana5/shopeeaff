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
