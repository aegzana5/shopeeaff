from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest
from youtube import post_short


def test_post_short_raises_if_no_client_secrets(tmp_path):
    with patch("youtube.YOUTUBE_CLIENT_SECRETS", str(tmp_path / "missing.json")):
        from youtube import post_short
        with pytest.raises(RuntimeError, match="client secrets not found"):
            post_short(tmp_path / "clip.mp4", "Test Title", "Test description")


def test_post_short_returns_video_id(tmp_path):
    """post_short returns video ID string on success."""
    # Create a dummy video file
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"fake mp4")

    # Create dummy client secrets so file-exists check passes
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text('{"installed": {}}')

    mock_creds = MagicMock()
    mock_creds.valid = True

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [(None, None), (None, {"id": "abc123"})]

    mock_videos = MagicMock()
    mock_videos.insert.return_value = mock_request

    mock_youtube = MagicMock()
    mock_youtube.videos.return_value = mock_videos

    with patch("youtube.YOUTUBE_CLIENT_SECRETS", str(secrets_file)), \
         patch("youtube.YOUTUBE_TOKEN_FILE", str(tmp_path / "token.json")), \
         patch("youtube._get_service", return_value=mock_youtube), \
         patch("youtube._prepare_yt_video", return_value=video_file), \
         patch("googleapiclient.http.MediaFileUpload") as mock_media:
        video_id = post_short(video_file, "My Product", "Great product description")
        assert video_id == "abc123"


def test_post_short_title_gets_shorts_hashtag(tmp_path):
    """Title has #Shorts appended."""
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"fake mp4")

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [(None, None), (None, {"id": "xyz"})]

    mock_videos = MagicMock()
    mock_videos.insert.return_value = mock_request

    mock_youtube = MagicMock()
    mock_youtube.videos.return_value = mock_videos

    with patch("youtube._get_service", return_value=mock_youtube), \
         patch("youtube._prepare_yt_video", return_value=video_file), \
         patch("googleapiclient.http.MediaFileUpload"):
        post_short(video_file, "My Product Name", "desc")
        call_kwargs = mock_videos.insert.call_args[1]
        title = call_kwargs["body"]["snippet"]["title"]
        assert "#Shorts" in title
        assert len(title) <= 100


def test_post_short_description_has_shorts_hashtag(tmp_path):
    """Description has #Shorts appended."""
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"fake mp4")

    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [(None, None), (None, {"id": "xyz"})]

    mock_videos = MagicMock()
    mock_videos.insert.return_value = mock_request

    mock_youtube = MagicMock()
    mock_youtube.videos.return_value = mock_videos

    with patch("youtube._get_service", return_value=mock_youtube), \
         patch("youtube._prepare_yt_video", return_value=video_file), \
         patch("googleapiclient.http.MediaFileUpload"):
        post_short(video_file, "Product", "My description")
        call_kwargs = mock_videos.insert.call_args[1]
        desc = call_kwargs["body"]["snippet"]["description"]
        assert "#Shorts" in desc
