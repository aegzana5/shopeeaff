"""Tests for instagram._verify_and_fix_caption."""
from unittest.mock import MagicMock, patch
import pytest


def _make_page(caption_text: str):
    """Build mock Playwright page using IG's caption container selector."""
    page = MagicMock()

    caption_loc = MagicMock()
    if caption_text:
        caption_loc.count.return_value = 1
        caption_loc.first.inner_text.return_value = caption_text
    else:
        caption_loc.count.return_value = 0

    edit_loc = MagicMock()
    edit_loc.first = MagicMock()

    def locator_side(sel):
        if '_a9zs' in sel or 'caption' in sel.lower():
            return caption_loc
        return edit_loc

    page.locator.side_effect = locator_side
    return page, edit_loc


def test_verify_caption_already_present_returns_true():
    """When caption exists on post, return True without triggering edit."""
    from instagram import _verify_and_fix_caption

    page, edit_locator = _make_page("Existing caption text")

    with patch("instagram.IG_USERNAME", "testuser"):
        result = _verify_and_fix_caption(page, "Existing caption text")

    assert result is True
    # No edit flow: get_by_role("menuitem") should never be called
    for call_args in page.get_by_role.call_args_list:
        assert call_args[0][0] != "menuitem", "Edit menuitem should not be clicked when caption is present"


def test_verify_caption_missing_triggers_edit_and_returns_true():
    """When caption is empty, trigger edit flow and use keyboard.type."""
    from instagram import _verify_and_fix_caption

    page, edit_locator = _make_page("")  # no caption

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time") as mock_time:
        mock_time.sleep = MagicMock()
        result = _verify_and_fix_caption(page, "My product caption")

    assert result is True
    # Edit menu item was clicked
    page.get_by_role.assert_any_call("menuitem", name="Edit")
    # Caption filled via keyboard.type not .fill()
    page.keyboard.type.assert_called_with("My product caption", delay=30)
    edit_locator.first.fill.assert_not_called()
    # Done button was clicked
    page.get_by_role.assert_any_call("button", name="Done")


def test_verify_fix_edit_uses_keyboard_type():
    """Edit flow in _verify_and_fix_caption must use keyboard.type not fill."""
    from instagram import _verify_and_fix_caption

    page, edit_loc = _make_page("")  # no caption → triggers edit

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        _verify_and_fix_caption(page, "ทดสอบ")

    page.keyboard.type.assert_called_with("ทดสอบ", delay=30)
    edit_loc.first.fill.assert_not_called()


def test_verify_caption_exception_returns_false():
    """Any Playwright exception returns False (non-fatal)."""
    from instagram import _verify_and_fix_caption

    page = MagicMock()
    page.goto.side_effect = Exception("network error")

    with patch("instagram.IG_USERNAME", "testuser"):
        result = _verify_and_fix_caption(page, "caption")

    assert result is False


def test_do_post_uses_keyboard_type_not_fill():
    """_do_post must use keyboard.type for caption, not fill()."""
    from pathlib import Path
    from instagram import _do_post

    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    # file input found on first try
    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    # caption field found immediately
    caption_loc = MagicMock()
    caption_loc.count.return_value = 1
    caption_loc.first = MagicMock()

    # "Next" button not found (already on caption step)
    next_btn = MagicMock()
    next_btn.count.return_value = 0

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        # Match actual CAPTION_SELECTORS
        if sel in [
            '[aria-label="Write a caption..."]',
            'textarea[aria-label*="caption"]',
            'div[aria-label*="caption"]',
            'div[role="textbox"]',
            'div[contenteditable="true"]',
        ]:
            return caption_loc
        return MagicMock(count=MagicMock(return_value=0))

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = next_btn
    page.get_by_text.return_value = MagicMock()
    page.evaluate.return_value = "Post shared"

    with patch("instagram.time"), \
         patch("instagram._verify_and_fix_caption", return_value=True):
        _do_post(page, Path("/tmp/fake.jpg"), "ทดสอบ caption")

    page.keyboard.type.assert_called_once_with("ทดสอบ caption", delay=30)
    caption_loc.first.click.assert_called_once()
    caption_loc.first.fill.assert_not_called()


def test_post_reel_clip_caption_uses_keyboard_type():
    """post_reel_clip must use keyboard.type for caption, not lc.fill()."""
    from pathlib import Path
    from instagram import post_reel_clip

    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    caption_lc = MagicMock()
    caption_lc.count.return_value = 1
    caption_lc.first = MagicMock()

    fill_calls = []
    caption_lc.first.fill.side_effect = fill_calls.append

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if any(k in sel for k in ['caption', 'textbox', 'contenteditable', 'textarea']):
            return caption_lc
        return MagicMock(count=MagicMock(return_value=0))

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = MagicMock(count=MagicMock(return_value=0))
    page.evaluate.return_value = "Reel shared"

    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._verify_and_fix_caption", return_value=True), \
         patch("instagram.time"):
        post_reel_clip(Path("/tmp/fake.mp4"), "ทดสอบ reel")

    page.keyboard.type.assert_called_with("ทดสอบ reel", delay=30)
    assert fill_calls == [], f"fill() called unexpectedly with: {fill_calls}"
