import json
import logging
import re
from collections import Counter
from pathlib import Path

log = logging.getLogger(__name__)

SIGNALS_PATH = Path("assets/trend_signals.json")

_CLIP_KEYWORD_MAP = [
    (["ก่อน", "หลัง", "before", "after"], "before_after"),
    (["pov", "POV"], "pov_meme"),
    (["ราคา", "price", "shock", "แพง", "ถูก"], "price_shock"),
    (["beat", "เสียง", "เพลง"], "beat_hook"),
]


def extract_signals(posts: list[dict]) -> dict:
    hooks = []
    clip_type_votes = []
    hashtag_counts = Counter()

    for post in posts:
        caption = post.get("caption", "")
        lines = [line.strip() for line in caption.splitlines() if line.strip()]
        if lines:
            hooks.append(lines[0])

        caption_lower = caption.lower()
        matched = False
        for keywords, ctype in _CLIP_KEYWORD_MAP:
            if any(kw.lower() in caption_lower for kw in keywords):
                clip_type_votes.append(ctype)
                matched = True
                break
        if not matched:
            clip_type_votes.append("multi")

        for tag in re.findall(r"#\S+", caption):
            hashtag_counts[tag.lower()] += 1

    type_counts = Counter(clip_type_votes)
    top_clip_types = [t for t, _ in type_counts.most_common(3)]

    trending_hashtags = [tag for tag, _ in hashtag_counts.most_common(10)]

    seen: set = set()
    unique_hooks = []
    for h in hooks:
        if h not in seen and len(unique_hooks) < 10:
            seen.add(h)
            unique_hooks.append(h)

    return {
        "hooks": unique_hooks,
        "top_clip_types": top_clip_types,
        "trending_hashtags": trending_hashtags,
    }


def save_signals(signals: dict) -> None:
    SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SIGNALS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(signals, ensure_ascii=False), encoding="utf-8")
    tmp.rename(SIGNALS_PATH)


def load_signals() -> dict:
    if not SIGNALS_PATH.exists():
        return {}
    try:
        return json.loads(SIGNALS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Failed to load trend signals: %s", e)
        return {}
