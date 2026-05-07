import json
import pytest
from pathlib import Path


SAMPLE_POSTS = [
    {
        "platform": "instagram",
        "post_id": "111",
        "url": "https://www.instagram.com/p/abc/",
        "caption": "ก่อนใส่ Shopee หลังใส่ Shopee 🔥\n#แฟชั่น #ootdthailand",
        "views": 50000,
        "likes": 5000,
        "source": "fashionpage",
        "source_type": "account",
    },
    {
        "platform": "tiktok",
        "post_id": "222",
        "url": "https://www.tiktok.com/@user/video/222",
        "caption": "POV: เจอเสื้อสวยราคาถูก 🥹\n#ShopeeTH #แฟชั่น",
        "views": 120000,
        "likes": 8000,
        "source": "แฟชั่น",
        "source_type": "hashtag",
    },
    {
        "platform": "instagram",
        "post_id": "333",
        "url": "https://www.instagram.com/p/xyz/",
        "caption": "ราคา vs Shopee 🤯\nลิ้งค์ด้านล่าง\n#shopee_th #ราคาถูก",
        "views": 30000,
        "likes": 2000,
        "source": "ราคาถูก",
        "source_type": "hashtag",
    },
]


def test_extract_signals_returns_hooks():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "hooks" in signals
    assert len(signals["hooks"]) == 3
    assert signals["hooks"][0] == "ก่อนใส่ Shopee หลังใส่ Shopee 🔥"


def test_extract_signals_infers_clip_types():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "top_clip_types" in signals
    assert len(signals["top_clip_types"]) >= 1
    assert "before_after" in signals["top_clip_types"] or "pov_meme" in signals["top_clip_types"]


def test_extract_signals_extracts_hashtags():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "trending_hashtags" in signals
    assert "#แฟชั่น" in signals["trending_hashtags"]


def test_load_signals_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("trend_signals.SIGNALS_PATH", tmp_path / "nonexistent.json")
    from trend_signals import load_signals
    result = load_signals()
    assert result == {}


def test_save_and_load_signals_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("trend_signals.SIGNALS_PATH", tmp_path / "signals.json")
    from trend_signals import save_signals, load_signals
    data = {"hooks": ["hook1"], "top_clip_types": ["pov_meme"], "trending_hashtags": ["#แฟชั่น"]}
    save_signals(data)
    result = load_signals()
    assert result == data
