import json
import logging
from datetime import datetime
from pathlib import Path

from shopee import get_trending_fashion, pick_top_items
from content_gen import generate_caption, generate_reel_script, generate_video_caption
from media_gen import create_post_image, create_reel
from instagram import post_image, post_reel
import random
from video_gen import create_clip, create_price_reveal_clip, create_countdown_clip
from viral_gen import (
    create_before_after_clip,
    create_pov_meme_clip,
    create_price_shock_clip,
    create_beat_hook_clip,
)
import tts
import stock_media
from tiktok import post_clip
from youtube import post_short
from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY, TREND_RESHARE_ENABLED
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
    """Replace TikTok bio CTA with direct URL for YouTube/Instagram."""
    if not url:
        return caption
    replaced = caption.replace("ลิ้งค์ใน bio นะ 🔗", f"🛒 {url}")
    if replaced == caption:
        replaced = f"{caption}\n🛒 {url}"
    return replaced


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
            media_id = post_image(img_path, caption_data["caption"])
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


def run_video_cycle():
    log.info("Starting video cycle")

    signals = load_signals()
    trending_hooks = signals.get("hooks", [])

    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee feed")
        return

    history = _load_video_history()
    all_items = pick_top_items(items, n=min(len(items), 200))
    fresh = [it for it in all_items if str(it.get("itemId", "")) not in history]

    if len(fresh) < CLIPS_PER_DAY * 3:
        log.warning("Video history nearly exhausted, resetting")
        history = set()
        fresh = all_items

    # Batch into groups of 3 items per clip
    clip_batches = [fresh[i:i + 3] for i in range(0, CLIPS_PER_DAY * 3, 3)][:CLIPS_PER_DAY]

    CLIP_TYPES = [
        "multi", "price_reveal", "countdown",
        "before_after", "pov_meme", "price_shock", "beat_hook",
    ]
    CLIP_TYPES = CLIP_TYPES + signals.get("top_clip_types", [])

    posted = 0
    for i, batch in enumerate(clip_batches):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_type = random.choice(CLIP_TYPES)
            clip_name = f"clip_{ts}_{i}"
            item = batch[0]

            if clip_type == "before_after":
                clip_path = create_before_after_clip(item, clip_name)
            elif clip_type == "pov_meme":
                clip_path = create_pov_meme_clip(item, clip_name)
            elif clip_type == "price_shock":
                clip_path = create_price_shock_clip(item, clip_name)
            elif clip_type == "beat_hook":
                clip_path = create_beat_hook_clip(item, clip_name)
            else:
                keywords = stock_media._extract_keywords(item["itemName"])
                vo_path = tts.generate_voiceover(item, clip_name)
                bg_path = stock_media.fetch_bg_video(keywords, clip_name)
                if clip_type == "price_reveal":
                    clip_path = create_price_reveal_clip(
                        item, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                    )
                elif clip_type == "countdown":
                    five_items = fresh[i * 3: i * 3 + 5]
                    if len(five_items) < 5:
                        five_items = (five_items * 5)[:5]
                    clip_path = create_countdown_clip(
                        five_items, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                    )
                else:
                    clip_path = create_clip(
                        batch, clip_name, voiceover_path=vo_path, bg_video_path=bg_path
                    )

            caption_data = generate_video_caption(item, extra_hooks=trending_hooks or None)
            caption = caption_data["caption"]
            title = item["itemName"][:100]
            affiliate_url = caption_data.get("affiliate_url", "")
            caption_with_link = _inject_link(caption, affiliate_url)

            try:
                if affiliate_url:
                    from tiktok import update_bio
                    update_bio(affiliate_url)
                post_clip(clip_path, caption)
                log.info(f"TikTok posted: {item['itemName'][:40]}")
            except Exception as e:
                log.error(f"TikTok post {i} failed: {e}")

            try:
                video_id = post_short(clip_path, title, caption_with_link)
                log.info(f"YouTube Short posted: {video_id}")
            except Exception as e:
                log.error(f"YouTube post {i} failed: {e}")

            try:
                from instagram import post_reel_clip
                post_reel_clip(clip_path, caption_with_link)
                log.info(f"Instagram Reel posted: {item['itemName'][:40]}")
            except Exception as e:
                log.error(f"Instagram Reel post {i} failed: {e}")

            # Mark all batch items as seen
            for it in batch:
                history.add(str(it.get("itemId", "")))
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
