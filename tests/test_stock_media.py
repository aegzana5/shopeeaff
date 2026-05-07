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
