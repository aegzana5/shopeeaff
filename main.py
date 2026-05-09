import json
import logging
from datetime import datetime
from pathlib import Path

from shopee import get_trending_fashion, pick_top_items
from content_gen import generate_caption, generate_reel_script, generate_video_caption, generate_outfit_caption, generate_first_comment
from media_gen import create_post_image, create_reel
from instagram import post_image, post_reel
import random
from video_gen import create_clip, create_price_reveal_clip, create_countdown_clip
from viral_gen import (
    create_before_after_clip,
    create_pov_meme_clip,
    create_price_shock_clip,
    create_beat_hook_clip,
    create_outfit_clip,
)
import tts
import stock_media
from youtube import post_short
from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY, TREND_RESHARE_ENABLED, OUTFIT_MATCHES
from trend_discovery import discover_all
from trend_reshare import reshare_story, find_shopee_match, generate_affiliate_clip, post_affiliate_clip
from trend_signals import extract_signals, save_signals, load_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/fashionbot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def _inject_link(caption: str, url: str) -> str:
    if not url:
        return caption
    return f"{caption}\n🛒 {url}"


def run_post_cycle():
    log.info("Starting post cycle")

    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee")
        return

    post_history = _load_post_history()
    all_top = pick_top_items(items, n=min(len(items), 200))
    fresh = [it for it in all_top if str(it.get("itemId", "")) not in post_history]
    if len(fresh) < IMAGE_POSTS_PER_DAY:
        log.warning("Post history nearly exhausted, resetting")
        post_history = set()
        fresh = all_top

    top_items = fresh[:POSTS_PER_DAY + 2]
    log.info(f"{len(top_items)} fresh items selected")

    image_items = top_items[:IMAGE_POSTS_PER_DAY]
    reel_batches = [top_items[IMAGE_POSTS_PER_DAY:IMAGE_POSTS_PER_DAY+3]] * REELS_PER_DAY

    posted = 0

    for i, item in enumerate(image_items):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = create_post_image(item, item["affiliateUrl"], f"post_{ts}_{i}")
            caption_data = generate_caption(item, post_type="image")
            first_comment = generate_first_comment(item)
            media_id = post_image(img_path, caption_data["caption"], hashtags=first_comment)
            log.info(f"Image posted: {media_id} — {item['itemName'][:40]}")
            post_history.add(str(item.get("itemId", "")))
            posted += 1
        except Exception as e:
            log.error(f"Image post {i} failed: {e}")

    for j, reel_items in enumerate(reel_batches):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            script = _parse_script(generate_reel_script(reel_items))
            reel_path = create_reel(reel_items, script, f"reel_{ts}_{j}")
            caption_data = generate_caption(reel_items[0], post_type="reel")
            media_id = post_reel(reel_path, caption_data["caption"])
            log.info(f"Reel posted: {media_id}")
            for ri in reel_items:
                post_history.add(str(ri.get("itemId", "")))
            posted += 1
        except Exception as e:
            log.error(f"Reel {j} failed: {e}")

    _save_post_history(post_history)
    log.info(f"Cycle done: {posted}/{POSTS_PER_DAY} posted")


_POST_HISTORY = Path("assets/post_history.json")
_POST_HISTORY_MAX = 50

_VIDEO_HISTORY = Path("assets/video_history.json")
_VIDEO_HISTORY_MAX = 90  # keep last 90 posted item IDs

_TREND_HISTORY = Path("assets/trend_history.json")
_TREND_HISTORY_MAX = 500


def _load_post_history() -> set:
    if _POST_HISTORY.exists():
        return set(json.loads(_POST_HISTORY.read_text()))
    return set()


def _save_post_history(history: set) -> None:
    items_list = list(history)[-_POST_HISTORY_MAX:]
    tmp = _POST_HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(items_list))
    tmp.rename(_POST_HISTORY)


def _load_trend_history() -> set:
    if _TREND_HISTORY.exists():
        return set(json.loads(_TREND_HISTORY.read_text()))
    return set()


def _save_trend_history(history: set) -> None:
    items_list = list(history)[-_TREND_HISTORY_MAX:]
    tmp = _TREND_HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(items_list))
    tmp.rename(_TREND_HISTORY)


def _load_video_history() -> set:
    if _VIDEO_HISTORY.exists():
        return set(json.loads(_VIDEO_HISTORY.read_text()))
    return set()


def _save_video_history(history: set) -> None:
    items_list = list(history)[-_VIDEO_HISTORY_MAX:]
    tmp = _VIDEO_HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(items_list))
    tmp.rename(_VIDEO_HISTORY)


def _fetch_clip_items() -> tuple[list, set]:
    """Return (fresh_items_up_to_CLIPS_PER_DAY, history_set)."""
    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee feed")
        return [], set()

    history = _load_video_history()
    all_items = pick_top_items(items, n=min(len(items), 200))
    fresh = [it for it in all_items if str(it.get("itemId", "")) not in history]

    if len(fresh) < CLIPS_PER_DAY:
        log.warning("Video history nearly exhausted, resetting")
        history = set()
        fresh = all_items

    return fresh[:CLIPS_PER_DAY], history


def _make_clip(item: dict, i: int, signals: dict) -> tuple:
    """Build one video clip. Returns (clip_path, title, caption_with_link)."""
    trending_hooks = signals.get("hooks", [])
    top_clip_types = signals.get("top_clip_types", [])

    CLIP_TYPES = [
        "price_reveal", "before_after", "pov_meme", "price_shock", "beat_hook",
        "outfit", "outfit",
    ]
    CLIP_TYPES = CLIP_TYPES + top_clip_types

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clip_type = random.choice(CLIP_TYPES)
    clip_name = f"clip_{ts}_{i}"

    if clip_type == "outfit":
        from outfit_matcher import find_outfit_matches
        from image_ai import generate_model_image, remove_bg
        matches = find_outfit_matches(item, n=OUTFIT_MATCHES)
        caption_data = generate_outfit_caption(item, matches)
        caption = caption_data["caption"]
        caption_body = caption_data.get("caption_body", caption)
        title = item["itemName"][:100]
        caption_with_link = caption_data.get("caption_with_links", caption)
        vo_path = tts.generate_voiceover_from_text(caption_body, clip_name)
        model_img = generate_model_image(item, clip_name) or remove_bg(item.get("imageUrl", ""), clip_name)
        clip_path = create_outfit_clip(
            item, matches, clip_name,
            model_image_path=model_img,
            voiceover_path=vo_path,
        )
    else:
        caption_data = generate_video_caption(item, extra_hooks=trending_hooks or None)
        caption = caption_data["caption"]
        caption_body = caption_data.get("caption_body", caption)
        title = item["itemName"][:100]
        affiliate_url = caption_data.get("affiliate_url", "")
        caption_with_link = _inject_link(caption, affiliate_url)
        vo_path = tts.generate_voiceover_from_text(caption_body, clip_name)
        keywords = stock_media._extract_keywords(item["itemName"])
        bg_path = stock_media.fetch_bg_video(keywords, clip_name)
        if clip_type == "before_after":
            clip_path = create_before_after_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "pov_meme":
            clip_path = create_pov_meme_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "price_shock":
            clip_path = create_price_shock_clip(item, clip_name, voiceover_path=vo_path)
        elif clip_type == "beat_hook":
            clip_path = create_beat_hook_clip(item, clip_name, voiceover_path=vo_path)
        else:
            clip_path = create_price_reveal_clip(
                item, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
            )

    first_comment = generate_first_comment(item)
    return clip_path, title, caption_with_link, first_comment


def _distribute_clip(clip_path, title: str, caption: str, item_name: str = "", hashtags: str = "") -> None:
    """Post clip to all active platforms. Each platform fails independently."""
    try:
        yt_title = title.strip() or item_name[:100] or "Fashion Find"
        video_id = post_short(clip_path, yt_title, caption)
        log.info(f"YouTube Short posted: {video_id}")
    except Exception as e:
        log.error(f"YouTube post failed: {e}")

    try:
        from instagram import post_reel_clip
        post_reel_clip(clip_path, caption, hashtags=hashtags)
        log.info(f"Instagram Reel posted: {item_name[:40]}")
    except Exception as e:
        log.error(f"Instagram Reel post failed: {e}")


def run_video_cycle():
    log.info("Starting video cycle")

    signals = load_signals()
    clip_items, history = _fetch_clip_items()
    if not clip_items:
        return

    posted = 0
    for i, item in enumerate(clip_items):
        try:
            clip_path, title, caption, first_comment = _make_clip(item, i, signals)
            _distribute_clip(clip_path, title, caption, item.get("itemName", ""), hashtags=first_comment)
            history.add(str(item.get("itemId", "")))
            posted += 1
        except Exception as e:
            log.error(f"Video clip {i} failed: {e}")

    _save_video_history(history)
    log.info(f"Video cycle done: {posted}/{CLIPS_PER_DAY} clips")


def run_trend_cycle():
    log.info("Starting trend cycle")

    posts = discover_all()
    if not posts:
        log.info("No viral posts found, skipping trend cycle")
        return

    trend_history = _load_trend_history()
    fresh_posts = [p for p in posts if p.get("post_id") not in trend_history]
    log.info("Trend posts: %d total, %d fresh (skipping %d seen)", len(posts), len(fresh_posts), len(posts) - len(fresh_posts))

    processed_ids = set()
    for post in fresh_posts:
        try:
            if TREND_RESHARE_ENABLED:
                reshare_story(post)
            item = find_shopee_match(post)
            if item:
                clip = generate_affiliate_clip(item, post)
                post_affiliate_clip(clip, item)
            processed_ids.add(post["post_id"])
        except Exception as e:
            log.error("Trend post %s failed: %s", post.get("post_id", "unknown"), e)

    trend_history.update(processed_ids)
    _save_trend_history(trend_history)

    signals = extract_signals(posts)
    save_signals(signals)
    log.info("Trend cycle done: %d posts processed", len(fresh_posts))


def _parse_script(raw: str) -> dict:
    result = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


if __name__ == "__main__":
    run_post_cycle()
    run_video_cycle()
    run_trend_cycle()
