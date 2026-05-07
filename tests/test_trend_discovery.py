import pytest
from unittest.mock import patch, MagicMock


FAKE_IG_MEDIA = MagicMock()
FAKE_IG_MEDIA.pk = 111222333
FAKE_IG_MEDIA.code = "AbCdEf"
FAKE_IG_MEDIA.caption_text = "เสื้อสวย #แฟชั่น"
FAKE_IG_MEDIA.view_count = 50000
FAKE_IG_MEDIA.play_count = 0
FAKE_IG_MEDIA.like_count = 3000


def test_discover_instagram_returns_filtered_posts():
    mock_cl = MagicMock()
    mock_cl.user_id_from_username.return_value = 9999
    mock_cl.user_medias.return_value = [FAKE_IG_MEDIA]
    mock_cl.hashtag_medias_top.return_value = []

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"), \
         patch("trend_discovery.config.TREND_MIN_VIEWS", 10000), \
         patch("trend_discovery.config.TREND_MIN_LIKES", 1000), \
         patch("trend_discovery.config.TREND_TOP_N", 3):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert len(results) == 1
    assert results[0]["platform"] == "instagram"
    assert results[0]["post_id"] == "111222333"
    assert results[0]["views"] == 50000


def test_discover_instagram_returns_empty_on_login_failure():
    mock_cl = MagicMock()
    mock_cl.login.side_effect = Exception("Login failed")

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert results == []


def test_discover_instagram_filters_below_threshold():
    low_media = MagicMock()
    low_media.pk = 555
    low_media.code = "low"
    low_media.caption_text = "test"
    low_media.view_count = 100
    low_media.play_count = 0
    low_media.like_count = 10

    mock_cl = MagicMock()
    mock_cl.user_id_from_username.return_value = 9999
    mock_cl.user_medias.return_value = [low_media]
    mock_cl.hashtag_medias_top.return_value = []

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"), \
         patch("trend_discovery.config.TREND_MIN_VIEWS", 10000), \
         patch("trend_discovery.config.TREND_MIN_LIKES", 1000), \
         patch("trend_discovery.config.TREND_TOP_N", 3):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert results == []


def test_discover_tiktok_returns_empty_when_disabled():
    with patch("trend_discovery.config.TIKTOKAPI_ENABLED", False):
        from trend_discovery import discover_tiktok
        results = discover_tiktok(["user"], ["tag"])
    assert results == []


def test_discover_all_deduplicates_by_post_id():
    post_a = {
        "platform": "instagram", "post_id": "SAME", "url": "u", "caption": "",
        "views": 50000, "likes": 3000, "source": "a", "source_type": "account",
    }
    post_b = {
        "platform": "tiktok", "post_id": "SAME", "url": "u2", "caption": "",
        "views": 60000, "likes": 4000, "source": "b", "source_type": "hashtag",
    }

    with patch("trend_discovery.discover_instagram", return_value=[post_a]), \
         patch("trend_discovery.discover_tiktok", return_value=[post_b]), \
         patch("trend_discovery.config.TREND_ACCOUNTS_INSTAGRAM", []), \
         patch("trend_discovery.config.TREND_ACCOUNTS_TIKTOK", []), \
         patch("trend_discovery.config.TREND_HASHTAGS", []):
        from trend_discovery import discover_all
        results = discover_all()

    assert len(results) == 1
    assert results[0]["post_id"] == "SAME"
