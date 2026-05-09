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
    """When caption is empty, trigger edit flow and fill caption via .fill()."""
    from instagram import _verify_and_fix_caption

    page, edit_locator = _make_page("")  # no caption
    page.evaluate.return_value = ""  # JS caption check returns empty → triggers edit

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time") as mock_time:
        mock_time.sleep = MagicMock()
        result = _verify_and_fix_caption(page, "My product caption")

    assert result is True
    # Edit menu item was clicked
    page.get_by_role.assert_any_call("menuitem", name="Edit")
    # Caption filled via .fill(), not keyboard.type
    page.keyboard.type.assert_not_called()
    # Done button was clicked
    page.get_by_role.assert_any_call("button", name="Done")


def test_verify_fix_edit_uses_fill_not_keyboard_type():
    """Edit flow in _verify_and_fix_caption must use fill() not keyboard.type."""
    from instagram import _verify_and_fix_caption

    page, edit_loc = _make_page("")  # no caption → triggers edit
    page.evaluate.return_value = ""  # JS caption check returns empty

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        _verify_and_fix_caption(page, "ทดสอบ")

    page.keyboard.type.assert_not_called()


def test_verify_caption_exception_returns_false():
    """Any Playwright exception returns False (non-fatal)."""
    from instagram import _verify_and_fix_caption

    page = MagicMock()
    page.goto.side_effect = Exception("network error")

    with patch("instagram.IG_USERNAME", "testuser"):
        result = _verify_and_fix_caption(page, "caption")

    assert result is False


def test_do_post_uses_fill_not_keyboard_type():
    """_do_post must use fill() for caption, not keyboard.type."""
    from pathlib import Path
    from instagram import _do_post

    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    caption_loc = MagicMock()
    caption_loc.count.return_value = 1
    caption_loc.first = MagicMock()

    def _null_loc():
        m = MagicMock()
        m.count.return_value = 0
        m.filter.return_value = m
        return m

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if sel in [
            '[aria-label="Write a caption..."]',
            '[aria-label*="caption"] div[contenteditable="true"]',
            'textarea[aria-label*="caption"]',
            'div[contenteditable="true"]',
            'textarea',
        ]:
            return caption_loc
        return _null_loc()

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = _null_loc()
    page.get_by_text.return_value = MagicMock()
    page.evaluate.return_value = "Post shared"

    with patch("instagram.time"), \
         patch("instagram._verify_and_fix_caption", return_value=True):
        _do_post(page, Path("/tmp/fake.jpg"), "ทดสอบ caption")

    page.keyboard.type.assert_not_called()
    caption_loc.first.click.assert_called_once()
    caption_loc.first.fill.assert_called_once_with("ทดสอบ caption")


def test_post_reel_clip_caption_uses_fill_not_keyboard_type():
    """post_reel_clip must use fill() for caption, not keyboard.type."""
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

    def _null_loc():
        m = MagicMock()
        m.count.return_value = 0
        m.filter.return_value = m
        return m

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if any(k in sel for k in ['caption', 'คำบรรยาย', 'contenteditable', 'textarea']):
            return caption_lc
        return _null_loc()

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = _null_loc()
    page.evaluate.return_value = "Reel shared"

    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._verify_and_fix_caption", return_value=True), \
         patch("instagram.time"):
        post_reel_clip(Path("/tmp/fake.mp4"), "ทดสอบ reel")

    page.keyboard.type.assert_not_called()
    caption_lc.first.fill.assert_called_once_with("ทดสอบ reel")


def test_post_first_comment_types_hashtags():
    """_post_first_comment clicks comment field and types hashtag block."""
    from instagram import _post_first_comment

    page = MagicMock()
    comment_loc = MagicMock()
    comment_loc.count.return_value = 1
    comment_loc.first = MagicMock()

    page.locator.return_value = comment_loc

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        result = _post_first_comment(page, "#แฟชั่น #ootd")

    assert result is True
    comment_loc.first.click.assert_called_once()
    page.keyboard.type.assert_called_once_with("#แฟชั่น #ootd", delay=10)
    page.keyboard.press.assert_called_once_with("Enter")


def test_post_first_comment_empty_returns_false():
    """_post_first_comment returns False immediately when hashtags empty."""
    from instagram import _post_first_comment

    page = MagicMock()
    result = _post_first_comment(page, "")
    assert result is False
    page.goto.assert_not_called()


def test_post_first_comment_exception_returns_false():
    """Any exception in _post_first_comment returns False without raising."""
    from instagram import _post_first_comment

    page = MagicMock()
    page.goto.side_effect = Exception("network error")

    with patch("instagram.IG_USERNAME", "testuser"), \
         patch("instagram.time"):
        result = _post_first_comment(page, "#แฟชั่น")

    assert result is False


def _make_post_image_page():
    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.frames = []

    file_loc = MagicMock()
    file_loc.count.return_value = 1
    file_loc.first = MagicMock()

    caption_loc = MagicMock()
    caption_loc.count.return_value = 1
    caption_loc.first = MagicMock()

    def _null_loc():
        m = MagicMock()
        m.count.return_value = 0
        m.filter.return_value = m
        return m

    def locator_side(sel):
        if 'type="file"' in sel:
            return file_loc
        if sel in [
            '[aria-label="Write a caption..."]',
            '[aria-label*="caption"] div[contenteditable="true"]',
            'textarea[aria-label*="caption"]',
            'div[contenteditable="true"]',
            'textarea',
        ]:
            return caption_loc
        return _null_loc()

    page.locator.side_effect = locator_side
    page.get_by_role.return_value = _null_loc()
    page.get_by_text.return_value = MagicMock()
    page.evaluate.return_value = "Post shared"
    return page


def test_post_image_calls_post_first_comment_when_hashtags_given():
    """post_image calls _post_first_comment when hashtags param provided."""
    from pathlib import Path
    from instagram import post_image

    page = _make_post_image_page()
    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._verify_and_fix_caption", return_value=True), \
         patch("instagram._post_first_comment") as mock_first_comment, \
         patch("instagram.time"):
        post_image(Path("/tmp/fake.jpg"), "caption", hashtags="#แฟชั่น #ootd")

    mock_first_comment.assert_called_once_with(page, "#แฟชั่น #ootd")


def test_post_image_no_hashtags_no_post_first_comment():
    """post_image does NOT call _post_first_comment when hashtags empty."""
    from pathlib import Path
    from instagram import post_image

    page = _make_post_image_page()
    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()

    with patch("instagram._make_context", return_value=(browser, ctx)), \
         patch("instagram._ensure_logged_in", return_value=True), \
         patch("instagram._verify_and_fix_caption", return_value=True), \
         patch("instagram._post_first_comment") as mock_first_comment, \
         patch("instagram.time"):
        post_image(Path("/tmp/fake.jpg"), "caption")

    mock_first_comment.assert_not_called()
