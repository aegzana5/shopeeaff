import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


FAKE_ITEM = {
    "itemName": "เสื้อยืดน่ารัก Korean Style",
    "priceDisplay": "299",
    "affiliateUrl": "https://s.shopee.co.th/abc",
}


def test_generate_voiceover_returns_mp3_path(tmp_path, monkeypatch):
    monkeypatch.setattr("tts.OUTPUT_DIR", tmp_path)
    fake_resp = MagicMock()
    fake_resp.content = b"ID3\x00fake-mp3-data"
    fake_resp.raise_for_status = MagicMock()

    with patch("tts.requests.post", return_value=fake_resp), \
         patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", "test-key"), \
         patch("tts.config.ELEVENLABS_VOICE_ID", "test-voice"):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")

    assert result is not None
    assert result.suffix == ".mp3"
    assert result.exists()


def test_generate_voiceover_returns_none_when_disabled():
    with patch("tts.config.TTS_ENABLED", False):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")
    assert result is None


def test_generate_voiceover_returns_none_when_no_api_key():
    with patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", ""):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")
    assert result is None


def test_generate_voiceover_returns_none_on_api_error(tmp_path, monkeypatch):
    import requests as req_lib
    monkeypatch.setattr("tts.OUTPUT_DIR", tmp_path)
    fake_resp = MagicMock()
    fake_resp.raise_for_status.side_effect = req_lib.HTTPError("401 Unauthorized")

    with patch("tts.requests.post", return_value=fake_resp), \
         patch("tts.config.TTS_ENABLED", True), \
         patch("tts.config.ELEVENLABS_API_KEY", "bad-key"), \
         patch("tts.config.ELEVENLABS_VOICE_ID", "test-voice"):
        import tts
        result = tts.generate_voiceover(FAKE_ITEM, "test_clip")

    assert result is None
