"""Tests for tiktok.py"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

pytest.importorskip("playwright", reason="playwright not installed")


# ---------------------------------------------------------------------------
# test_load_cookies_raises_if_no_session_file
# ---------------------------------------------------------------------------

def test_load_cookies_raises_if_no_session_file(tmp_path, monkeypatch):
    """RuntimeError when session file does not exist."""
    import tiktok
    monkeypatch.setattr(tiktok, "SESSION_FILE", tmp_path / "nonexistent.json")
    with pytest.raises(RuntimeError, match="No TikTok session found"):
        tiktok._load_cookies()


# ---------------------------------------------------------------------------
# test_load_cookies_returns_list
# ---------------------------------------------------------------------------

def test_load_cookies_returns_list(tmp_path, monkeypatch):
    """Returns list of cookies from valid JSON session file."""
    import tiktok

    session_file = tmp_path / "tiktok_session.json"
    session_file.write_text(
        json.dumps({"cookies": [{"name": "sessionid", "value": "abc"}]})
    )
    monkeypatch.setattr(tiktok, "SESSION_FILE", session_file)

    result = tiktok._load_cookies()
    assert isinstance(result, list)
    assert result[0]["name"] == "sessionid"
    assert result[0]["value"] == "abc"


# ---------------------------------------------------------------------------
# test_post_clip_raises_on_expired_session
# ---------------------------------------------------------------------------

def test_post_clip_raises_on_expired_session(tmp_path):
    """RuntimeError with exact message when page.url contains 'login'."""
    import tiktok

    # Build mock playwright chain
    mock_page = MagicMock()
    mock_page.url = "https://www.tiktok.com/login/"

    mock_ctx = MagicMock()
    mock_ctx.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_ctx

    mock_page.frames = []

    mock_p = MagicMock()
    mock_p.webkit.launch.return_value = mock_browser  # code uses webkit not chromium

    mock_playwright_cm = MagicMock()
    mock_playwright_cm.__enter__ = MagicMock(return_value=mock_p)
    mock_playwright_cm.__exit__ = MagicMock(return_value=False)

    with patch("tiktok._load_cookies", return_value=[{"name": "sid", "value": "x"}]):
        with patch("tiktok.sync_playwright", return_value=mock_playwright_cm):
            with patch("tiktok.time") as mock_time:
                mock_time.sleep = MagicMock()
                with pytest.raises(RuntimeError) as exc_info:
                    tiktok.post_clip(tmp_path / "clip.mp4", "test caption")
    assert str(exc_info.value) == "TikTok session expired. Run: python3 setup_tiktok.py"


# ---------------------------------------------------------------------------
# test_post_clip_returns_posted_on_success
# ---------------------------------------------------------------------------

def test_post_clip_returns_posted_on_success(tmp_path):
    """Returns 'posted' when the full upload flow succeeds."""
    import tiktok

    # File chooser mock
    mock_fc_value = MagicMock()
    mock_fc_cm = MagicMock()
    mock_fc_cm.__enter__ = MagicMock(return_value=mock_fc_cm)
    mock_fc_cm.__exit__ = MagicMock(return_value=False)
    mock_fc_cm.value = mock_fc_value

    # Locator mock — always reports count > 0
    def make_locator():
        lc = MagicMock()
        lc.count.return_value = 1
        return lc

    # Frame mock with file input so the upload path succeeds
    mock_frame = MagicMock()
    file_input_loc = MagicMock()
    file_input_loc.count.return_value = 1
    file_input_loc.first = MagicMock()
    mock_frame.locator.side_effect = lambda sel: file_input_loc if 'type="file"' in sel else make_locator()

    mock_page = MagicMock()
    mock_page.url = "https://www.tiktok.com/upload"
    mock_page.expect_file_chooser.return_value = mock_fc_cm
    mock_page.locator.side_effect = lambda sel: make_locator()
    mock_page.frames = [mock_frame]

    mock_ctx = MagicMock()
    mock_ctx.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_ctx

    mock_p = MagicMock()
    mock_p.webkit.launch.return_value = mock_browser  # code uses webkit not chromium

    mock_playwright_cm = MagicMock()
    mock_playwright_cm.__enter__ = MagicMock(return_value=mock_p)
    mock_playwright_cm.__exit__ = MagicMock(return_value=False)

    # Create a dummy video file so Path.absolute() works
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"fake")

    with patch("tiktok._load_cookies", return_value=[{"name": "sid", "value": "x"}]):
        with patch("tiktok.sync_playwright", return_value=mock_playwright_cm):
            with patch("tiktok.time") as mock_time:
                mock_time.sleep = MagicMock()
                result = tiktok.post_clip(video_file, "test caption")

    assert result == "posted"
    # Verify goto was called with TikTok upload URL
    mock_page.goto.assert_called_once()
    goto_url = mock_page.goto.call_args[0][0]
    assert "tiktok.com/upload" in goto_url
    # Verify file was set via set_input_files on the frame's file input
    file_input_loc.first.set_input_files.assert_called_once()
