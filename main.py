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
from tiktok import post_clip
from youtube import post_short
from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/fashionbot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def run_post_cycle():
    log.info("Starting post cycle")

    items = get_trending_fashion()
    if not items:
        log.error("No items from Shopee")
        return

    top_items = pick_top_items(items, n=POSTS_PER_DAY + 2)
    log.info(f"{len(top_items)} items selected")

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
            posted += 1
        except Exception as e:
            log.error(f"Reel {j} failed: {e}")

    log.info(f"Cycle done: {posted}/{POSTS_PER_DAY} posted")


_VIDEO_HISTORY = Path("assets/video_history.json")
_VIDEO_HISTORY_MAX = 90  # keep last 90 posted item IDs


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

    CLIP_TYPES = ["multi", "price_reveal", "countdown"]

    posted = 0
    for i, batch in enumerate(clip_batches):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_type = random.choice(CLIP_TYPES)

            if clip_type == "price_reveal":
                clip_path = create_price_reveal_clip(batch[0], f"clip_{ts}_{i}")
            elif clip_type == "countdown":
                five_items = fresh[i * 3: i * 3 + 5]
                if len(five_items) < 5:
                    five_items = (five_items * 5)[:5]
                clip_path = create_countdown_clip(five_items, f"clip_{ts}_{i}")
            else:
                clip_path = create_clip(batch, f"clip_{ts}_{i}")

            # Use first item for caption/title
            item = batch[0]
            caption_data = generate_video_caption(item)
            caption = caption_data["caption"]
            title = item["itemName"][:100]

            try:
                post_clip(clip_path, caption)
                log.info(f"TikTok posted: {item['itemName'][:40]}")
            except Exception as e:
                log.error(f"TikTok post {i} failed: {e}")

            try:
                video_id = post_short(clip_path, title, caption)
                log.info(f"YouTube Short posted: {video_id}")
            except Exception as e:
                log.error(f"YouTube post {i} failed: {e}")

            try:
                from instagram import post_reel_clip
                post_reel_clip(clip_path, caption)
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
