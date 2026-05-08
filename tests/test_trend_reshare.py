import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


FAKE_ITEM = {
    "itemName": "เสื้อยืด Korean Style",
    "priceDisplay": "299",
    "affiliateUrl": "https://s.shopee.co.th/abc",
    "itemId": "123",
    "imageUrl": "https://img.shopee.co.th/1.jpg",
    "sales": 500,
    "ratingStar": 4.5,
    "shopName": "KoreanFashion",
    "price": "299",
}

IG_POST = {
    "platform": "instagram",
    "post_id": "111222333",
    "url": "https://www.instagram.com/p/AbCdEf/",
    "caption": "ก่อนเจอ Shopee หลังเจอ Shopee 🔥 #แฟชั่น",
    "views": 50000,
    "likes": 3000,
    "source": "fashionpage",
    "source_type": "account",
}

TK_POST = {
    "platform": "tiktok",
    "post_id": "7123456789",
    "url": "https://www.tiktok.com/@user/video/7123456789",
    "caption": "POV: เจอเสื้อสวยราคาถูก 🥹",
    "views": 120000,
    "likes": 8000,
    "source": "tiktokfashion",
    "source_type": "account",
}


def test_find_shopee_match_returns_item_when_match_found():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="korean shirt")]

    with patch("trend_reshare.anthropic.Anthropic") as mock_cls, \
         patch("trend_reshare.search_products", return_value=[FAKE_ITEM]):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_msg
        mock_cls.return_value = mock_client

        from trend_reshare import find_shopee_match
        result = find_shopee_match(IG_POST)

    assert result is not None
    assert result["itemName"] == "เสื้อยืด Korean Style"


def test_find_shopee_match_returns_none_when_search_empty():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="dress")]

    with patch("trend_reshare.anthropic.Anthropic") as mock_cls, \
         patch("trend_reshare.search_products", return_value=[]):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_msg
        mock_cls.return_value = mock_client

        from trend_reshare import find_shopee_match
        result = find_shopee_match(TK_POST)

    assert result is None


def test_generate_affiliate_clip_picks_before_after_format(tmp_path):
    post = dict(IG_POST, caption="ก่อนเจอ Shopee หลังเจอ Shopee 🔥")
    fake_path = tmp_path / "trend_abc.mp4"
    fake_path.write_bytes(b"fake")

    with patch("trend_reshare.create_before_after_clip", return_value=fake_path) as mock_ba, \
         patch("trend_reshare.create_pov_meme_clip") as mock_pov, \
         patch("trend_reshare.create_price_shock_clip") as mock_ps, \
         patch("trend_reshare.create_beat_hook_clip") as mock_bh:
        from trend_reshare import generate_affiliate_clip
        result = generate_affiliate_clip(FAKE_ITEM, post)

    mock_ba.assert_called_once()
    mock_pov.assert_not_called()
    assert result == fake_path


def test_reshare_story_returns_false_on_instagrapi_error():
    mock_cl = MagicMock()
    mock_cl.login.side_effect = Exception("Auth failed")

    with patch("trend_reshare.Client", return_value=mock_cl), \
         patch("trend_reshare.config.IG_USERNAME", "user"), \
         patch("trend_reshare.config.IG_PASSWORD", "pass"):
        from trend_reshare import reshare_story
        result = reshare_story(IG_POST)

    assert result is False
