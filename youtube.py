"""
YouTube Shorts upload via YouTube Data API v3.
OAuth2 token stored at config.YOUTUBE_TOKEN_FILE.
First run opens browser for Google consent.
"""
import logging
from pathlib import Path

from config import YOUTUBE_TOKEN_FILE, YOUTUBE_CLIENT_SECRETS

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SHORTS_HASHTAG = "#Shorts"


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = Path(YOUTUBE_TOKEN_FILE)
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS)

    if not secrets_path.exists():
        raise RuntimeError(
            f"YouTube client secrets not found at {secrets_path}. "
            "Download from Google Cloud Console → APIs & Services → Credentials."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def post_short(video_path: Path, title: str, description: str) -> str:
    """Upload video as YouTube Short. Returns video ID."""
    from googleapiclient.http import MediaFileUpload

    youtube = _get_service()
    video_path = Path(video_path).absolute()

    suffix = f" {SHORTS_HASHTAG}"  # " #Shorts" = 8 chars
    max_title_len = 100 - len(suffix)  # 92
    short_title = f"{title[:max_title_len]}{suffix}"

    body = {
        "snippet": {
            "title": short_title,
            "description": f"{description}\n\n{SHORTS_HASHTAG}",
            "tags": ["Shorts", "ShopeeThailand", "แฟชั่น", "fashion", "OOTDThailand"],
            "categoryId": "26",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    max_chunks = 200
    for _ in range(max_chunks):
        _, response = request.next_chunk()
        if response is not None:
            break
    else:
        raise RuntimeError("YouTube upload stalled after too many chunks")

    video_id = response["id"]
    log.info("YouTube Short uploaded: https://youtube.com/shorts/%s", video_id)
    return video_id
