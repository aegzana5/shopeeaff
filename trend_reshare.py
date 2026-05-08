import logging
import tempfile
import time
from pathlib import Path

import anthropic
import requests

import config
from shopee import search_products
from viral_gen import (
    create_before_after_clip,
    create_pov_meme_clip,
    create_price_shock_clip,
    create_beat_hook_clip,
)

log = logging.getLogger(__name__)

try:
    from instagrapi import Client
except ImportError:
    Client = None

_ig_client: "Client | None" = None


def _get_ig_client() -> "Client | None":
    global _ig_client
    if _ig_client is not None:
        return _ig_client
    if Client is None:
        return None
    try:
        cl = Client()
        session_file = Path(config.IG_SESSION_FILE)
        if session_file.exists():
            cl.load_settings(str(session_file))
        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        cl.dump_settings(str(session_file))
        _ig_client = cl
        return _ig_client
    except Exception as e:
        log.warning("Instagram login failed: %s", e)
        return None

_CLIP_FORMAT_MAP = [
    (["ก่อน", "หลัง", "before", "after"], "before_after"),
    (["pov", "POV"], "pov_meme"),
    (["ราคา", "price", "shock", "แพง", "ถูก"], "price_shock"),
]


def reshare_story(post: dict) -> bool:
    if post["platform"] == "instagram":
        return _reshare_instagram_story(post)
    return False


def _reshare_instagram_story(post: dict) -> bool:
    try:
        if Client is None:
            log.warning("instagrapi not installed, skipping Instagram story reshare")
            return False
        cl = _get_ig_client()
        if cl is None:
            return False
        media_info = cl.media_info(int(post["post_id"]))
        thumb_url = str(media_info.thumbnail_url) if media_info.thumbnail_url else None
        if not thumb_url:
            log.warning("thumbnail_url is None for post %s, skipping reshare", post["post_id"])
            return False
        resp = requests.get(thumb_url, timeout=30)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(resp.content)
            tmp_path = Path(f.name)
        cl.photo_upload_to_story(tmp_path)
        tmp_path.unlink(missing_ok=True)
        log.info("Instagram story reshare: %s", post["post_id"])
        return True
    except Exception as e:
        log.warning("Instagram story reshare failed: %s", e)
        return False



def find_shopee_match(post: dict) -> dict | None:
    caption = post.get("caption", "").strip()
    if not caption:
        return None
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": (
                    "Extract 2-4 product search keywords from this Thai fashion social media "
                    "caption for a Shopee product search. Return ONLY keywords space-separated, "
                    "no explanation, no punctuation.\n\nCaption: " + caption[:300]
                ),
            }],
        )
        if not msg.content or not hasattr(msg.content[0], "text"):
            log.warning("Claude returned empty or non-text content for caption: %s", caption[:80])
            return None
        query = msg.content[0].text.strip()
    except Exception as e:
        log.warning("Claude keyword extraction failed: %s", e)
        return None
    if not query:
        return None
    results = search_products(query)
    return results[0] if results else None


def generate_affiliate_clip(item: dict, post: dict) -> Path:
    from content_gen import generate_video_caption
    import tts as tts_mod
    caption_lower = post.get("caption", "").lower()
    clip_type = "beat_hook"
    for keywords, ctype in _CLIP_FORMAT_MAP:
        if any(kw.lower() in caption_lower for kw in keywords):
            clip_type = ctype
            break
    output_name = f"trend_{post['post_id'][:20]}"
    caption_data = generate_video_caption(item)
    caption_body = caption_data.get("caption_body", "")
    vo_path = tts_mod.generate_voiceover_from_text(caption_body, output_name) if caption_body else None
    if clip_type == "before_after":
        return create_before_after_clip(item, output_name, voiceover_path=vo_path)
    elif clip_type == "pov_meme":
        return create_pov_meme_clip(item, output_name, voiceover_path=vo_path)
    elif clip_type == "price_shock":
        return create_price_shock_clip(item, output_name, voiceover_path=vo_path)
    else:
        return create_beat_hook_clip(item, output_name, voiceover_path=vo_path)


def post_affiliate_clip(clip_path: Path, item: dict) -> None:
    from content_gen import generate_video_caption
    from youtube import post_short
    caption_data = generate_video_caption(item)
    caption = caption_data["caption"]
    title = item["itemName"][:100]
    affiliate_url = item.get("affiliateUrl", "")
    caption_with_link = f"{caption}\n🛒 {affiliate_url}" if affiliate_url else caption
    try:
        post_short(clip_path, title, caption_with_link)
        log.info("YouTube affiliate posted: %s", item["itemName"][:40])
    except Exception as e:
        log.error("YouTube affiliate post failed: %s", e)
    try:
        from instagram import post_reel_clip
        post_reel_clip(clip_path, caption_with_link)
        log.info("Instagram affiliate posted: %s", item["itemName"][:40])
    except Exception as e:
        log.error("Instagram affiliate post failed: %s", e)
