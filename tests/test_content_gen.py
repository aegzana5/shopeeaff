"""Tests for content_gen caption generation."""
from unittest.mock import MagicMock, patch
import pytest

FAKE_ITEM = {
    "itemName": "เสื้อครอปแขนกุด สีพาสเทล ลายดอกไม้",
    "priceDisplay": "199",
    "ratingStar": "4.8",
    "shopName": "FashionShopTH",
    "affiliateUrl": "https://shp.ee/test",
}


def _mock_claude(text: str):
    content = MagicMock()
    content.text = text
    msg = MagicMock()
    msg.content = [content]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


def test_generate_caption_caption_equals_body_no_hashtags():
    """generate_caption: caption key must equal caption_body (no hashtags appended)."""
    from content_gen import generate_caption

    with patch("content_gen.client", _mock_claude("Hook\nBenefit\nราคา 199 บาท\nกดลิ้งค์ใน bio 👆")):
        result = generate_caption(FAKE_ITEM, post_type="image")

    assert result["caption"] == result["caption_body"]
    assert "#" not in result["caption"]


def test_generate_caption_hashtags_key_is_nonempty_string():
    """generate_caption: hashtags key must be non-empty string starting with #."""
    from content_gen import generate_caption

    with patch("content_gen.client", _mock_claude("Hook\nBenefit\nราคา\nCTA")):
        result = generate_caption(FAKE_ITEM)

    assert isinstance(result["hashtags"], str)
    assert result["hashtags"].startswith("#")


def test_generate_caption_prompt_is_thai_only():
    """Claude prompt must not request English section."""
    from content_gen import generate_caption

    captured = []

    def capture_create(**kwargs):
        captured.append(kwargs["messages"][0]["content"])
        content = MagicMock()
        content.text = "Hook\nBenefit\nราคา 199\nCTA"
        msg = MagicMock()
        msg.content = [content]
        return msg

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = capture_create

    with patch("content_gen.client", mock_client):
        generate_caption(FAKE_ITEM)

    prompt = captured[0]
    assert "English" not in prompt


def test_generate_video_caption_caption_equals_body():
    """generate_video_caption: caption key must equal caption_body (no hashtags)."""
    from content_gen import generate_video_caption

    with patch("content_gen.client", _mock_claude("Hook\nBody\nราคา 199\n🛒 ลิ้งค์")):
        result = generate_video_caption(FAKE_ITEM)

    assert result["caption"] == result["caption_body"]
    assert "#" not in result["caption"]
