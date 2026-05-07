# Viral Trend Repost & Affiliate Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover viral Thai fashion posts on TikTok + Instagram, reshare to Stories natively, and when a Shopee product match is found, generate and post a new affiliate clip to all platforms.

**Architecture:** Four new modules (`trend_discovery.py`, `trend_reshare.py`, `trend_signals.py`) plus updates to `shopee.py`, `content_gen.py`, and `main.py`. Trend signals from discovered posts bias clip type selection in `run_video_cycle`. All external API calls degrade gracefully.

**Tech Stack:** instagrapi (Instagram discovery + Story reshare), TikTokApi unofficial (async, Playwright-backed), Playwright (TikTok Repost), Anthropic claude-haiku (keyword extraction), existing viral_gen + posting pipeline.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `trend_discovery.py` | Create | Discover viral posts from Instagram accounts/hashtags + TikTok |
| `trend_reshare.py` | Create | Reshare to Stories; find Shopee match; generate + post affiliate clip |
| `trend_signals.py` | Create | Extract hooks/clip-type hints from posts; save/load `assets/trend_signals.json` |
| `shopee.py` | Modify | Add `search_products(query)` — keyword search over cached feed |
| `content_gen.py` | Modify | `generate_video_caption` accepts optional `extra_hooks` list |
| `main.py` | Modify | Add `run_trend_cycle()`; bias `run_video_cycle` using trend signals |
| `config.py` | Modify | 8 new env vars for accounts, hashtags, thresholds, feature flags |
| `.env.example` | Modify | Document new vars |
| `requirements.txt` | Modify | Add `TikTokApi>=6.0.0` |
| `tests/test_trend_discovery.py` | Create | Mock instagrapi + TikTokApi; assert filtering |
| `tests/test_trend_reshare.py` | Create | Mock Claude + search_products + instagrapi; assert affiliate flow |
| `tests/test_trend_signals.py` | Create | Assert extraction from sample captions; assert load fallback |

---

## Task 1: Config, requirements, env

**Files:**
- Modify: `config.py`
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add 8 new env vars to config.py**

Append after line 45 (`STOCK_MEDIA_ENABLED = ...`):

```python
TREND_ACCOUNTS_INSTAGRAM = [a for a in os.getenv("TREND_ACCOUNTS_INSTAGRAM", "").split(",") if a]
TREND_ACCOUNTS_TIKTOK    = [a for a in os.getenv("TREND_ACCOUNTS_TIKTOK", "").split(",") if a]
TREND_HASHTAGS           = [h for h in os.getenv("TREND_HASHTAGS", "แฟชั่น,ootdthailand,shopee_th").split(",") if h]
TREND_MIN_VIEWS          = int(os.getenv("TREND_MIN_VIEWS", "10000"))
TREND_MIN_LIKES          = int(os.getenv("TREND_MIN_LIKES", "1000"))
TREND_TOP_N              = int(os.getenv("TREND_TOP_N", "3"))
TREND_RESHARE_ENABLED    = os.getenv("TREND_RESHARE_ENABLED", "true").lower() == "true"
TIKTOKAPI_ENABLED        = os.getenv("TIKTOKAPI_ENABLED", "true").lower() == "true"
```

- [ ] **Step 2: Add TikTokApi to requirements.txt**

Append:
```
TikTokApi>=6.0.0
```

- [ ] **Step 3: Add new vars to .env.example**

Append:
```
# Viral Trend Discovery
# Comma-separated Instagram account usernames to monitor (no @)
TREND_ACCOUNTS_INSTAGRAM=fashionbrand1,fashionbrand2
# Comma-separated TikTok usernames to monitor (no @)
TREND_ACCOUNTS_TIKTOK=tiktokfashion1
# Comma-separated hashtags to monitor (no #)
TREND_HASHTAGS=แฟชั่น,ootdthailand,shopee_th
# Minimum view count to consider a post viral
TREND_MIN_VIEWS=10000
# Minimum like count to consider a post viral (either threshold triggers)
TREND_MIN_LIKES=1000
# Max posts to action per source per cycle
TREND_TOP_N=3
# Set to false to skip Story resharing
TREND_RESHARE_ENABLED=true
# Set to false to skip TikTok discovery (if TikTokApi is unstable)
TIKTOKAPI_ENABLED=true
```

- [ ] **Step 4: Verify imports work**

```bash
cd /Users/aegisen/fashion-bot && python -c "import config; print(config.TREND_MIN_VIEWS, config.TREND_HASHTAGS)"
```

Expected: `10000 ['แฟชั่น', 'ootdthailand', 'shopee_th']`

- [ ] **Step 5: Commit**

```bash
git add config.py requirements.txt .env.example
git commit -m "feat: add trend discovery config vars and TikTokApi dependency"
```

---

## Task 2: shopee.search_products + tests

**Files:**
- Modify: `shopee.py`
- Modify: `tests/test_shopee.py`

- [ ] **Step 1: Write failing test**

Open `tests/test_shopee.py` and append:

```python
def test_search_products_returns_matches():
    items = [
        {"itemName": "เสื้อยืด Korean Style", "sales": 100, "itemId": "1",
         "price": "299", "priceDisplay": "299", "imageUrl": "https://img/1.jpg",
         "affiliateUrl": "https://s.shopee.co.th/1", "shopName": "shop", "ratingStar": 4.5},
        {"itemName": "กางเกงยีนส์แฟชั่น", "sales": 50, "itemId": "2",
         "price": "499", "priceDisplay": "499", "imageUrl": "https://img/2.jpg",
         "affiliateUrl": "https://s.shopee.co.th/2", "shopName": "shop", "ratingStar": 4.0},
        {"itemName": "ชุดเดรสสีชมพู", "sales": 200, "itemId": "3",
         "price": "599", "priceDisplay": "599", "imageUrl": "https://img/3.jpg",
         "affiliateUrl": "https://s.shopee.co.th/3", "shopName": "shop", "ratingStar": 4.8},
    ]
    with patch("shopee.get_trending_fashion", return_value=items):
        from shopee import search_products
        results = search_products("korean shirt")
    assert len(results) >= 1
    assert any("Korean" in r["itemName"] for r in results)


def test_search_products_returns_empty_on_no_match():
    items = [
        {"itemName": "โทรศัพท์มือถือ Samsung", "sales": 500, "itemId": "99",
         "price": "5000", "priceDisplay": "5000", "imageUrl": "https://img/99.jpg",
         "affiliateUrl": "https://s.shopee.co.th/99", "shopName": "tech", "ratingStar": 4.0},
    ]
    with patch("shopee.get_trending_fashion", return_value=items):
        from shopee import search_products
        results = search_products("dress fashion")
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_shopee.py::test_search_products_returns_matches -v
```

Expected: FAIL with `ImportError` or `AttributeError: module 'shopee' has no attribute 'search_products'`

- [ ] **Step 3: Implement search_products in shopee.py**

Append to `shopee.py` after `pick_top_items`:

```python
def search_products(query: str) -> list[dict]:
    """Search cached feed items by keyword match on itemName. Returns up to 10 results sorted by sales."""
    items = get_trending_fashion()
    query_lower = query.lower()
    keywords = [k for k in query_lower.split() if len(k) > 1]
    if not keywords:
        return []
    matches = [
        item for item in items
        if any(kw in item["itemName"].lower() for kw in keywords)
    ]
    return sorted(matches, key=lambda x: x["sales"], reverse=True)[:10]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_shopee.py -v
```

Expected: all tests pass including the 2 new ones

- [ ] **Step 5: Commit**

```bash
git add shopee.py tests/test_shopee.py
git commit -m "feat: add search_products() keyword search over cached Shopee feed"
```

---

## Task 3: trend_signals.py + tests

**Files:**
- Create: `trend_signals.py`
- Create: `tests/test_trend_signals.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trend_signals.py`:

```python
import json
import pytest
from pathlib import Path


SAMPLE_POSTS = [
    {
        "platform": "instagram",
        "post_id": "111",
        "url": "https://www.instagram.com/p/abc/",
        "caption": "ก่อนใส่ Shopee หลังใส่ Shopee 🔥\n#แฟชั่น #ootdthailand",
        "views": 50000,
        "likes": 5000,
        "source": "fashionpage",
        "source_type": "account",
    },
    {
        "platform": "tiktok",
        "post_id": "222",
        "url": "https://www.tiktok.com/@user/video/222",
        "caption": "POV: เจอเสื้อสวยราคาถูก 🥹\n#ShopeeTH #แฟชั่น",
        "views": 120000,
        "likes": 8000,
        "source": "แฟชั่น",
        "source_type": "hashtag",
    },
    {
        "platform": "instagram",
        "post_id": "333",
        "url": "https://www.instagram.com/p/xyz/",
        "caption": "ราคา vs Shopee 🤯\nลิ้งค์ด้านล่าง\n#shopee_th #ราคาถูก",
        "views": 30000,
        "likes": 2000,
        "source": "ราคาถูก",
        "source_type": "hashtag",
    },
]


def test_extract_signals_returns_hooks():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "hooks" in signals
    assert len(signals["hooks"]) == 3
    assert signals["hooks"][0] == "ก่อนใส่ Shopee หลังใส่ Shopee 🔥"


def test_extract_signals_infers_clip_types():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "top_clip_types" in signals
    assert len(signals["top_clip_types"]) >= 1
    # "ก่อน/หลัง" → before_after; "POV" → pov_meme; "ราคา" → price_shock
    assert "before_after" in signals["top_clip_types"] or "pov_meme" in signals["top_clip_types"]


def test_extract_signals_extracts_hashtags():
    from trend_signals import extract_signals
    signals = extract_signals(SAMPLE_POSTS)
    assert "trending_hashtags" in signals
    assert "#แฟชั่น" in signals["trending_hashtags"]


def test_load_signals_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("trend_signals.SIGNALS_PATH", tmp_path / "nonexistent.json")
    from trend_signals import load_signals
    result = load_signals()
    assert result == {}


def test_save_and_load_signals_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("trend_signals.SIGNALS_PATH", tmp_path / "signals.json")
    from trend_signals import save_signals, load_signals
    data = {"hooks": ["hook1"], "top_clip_types": ["pov_meme"], "trending_hashtags": ["#แฟชั่น"]}
    save_signals(data)
    result = load_signals()
    assert result == data
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_signals.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'trend_signals'`

- [ ] **Step 3: Create trend_signals.py**

Create `/Users/aegisen/fashion-bot/trend_signals.py`:

```python
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

        for tag in re.findall(r"#\w+", caption):
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_signals.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add trend_signals.py tests/test_trend_signals.py
git commit -m "feat: add trend_signals module for hook/clip-type extraction from viral posts"
```

---

## Task 4: trend_discovery.py + tests

**Files:**
- Create: `trend_discovery.py`
- Create: `tests/test_trend_discovery.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trend_discovery.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


FAKE_IG_MEDIA = MagicMock()
FAKE_IG_MEDIA.pk = 111222333
FAKE_IG_MEDIA.code = "AbCdEf"
FAKE_IG_MEDIA.caption_text = "เสื้อสวย #แฟชั่น"
FAKE_IG_MEDIA.view_count = 50000
FAKE_IG_MEDIA.play_count = 0
FAKE_IG_MEDIA.like_count = 3000


def test_discover_instagram_returns_filtered_posts():
    mock_cl = MagicMock()
    mock_cl.user_id_from_username.return_value = 9999
    mock_cl.user_medias.return_value = [FAKE_IG_MEDIA]
    mock_cl.hashtag_medias_top.return_value = []

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"), \
         patch("trend_discovery.config.TREND_MIN_VIEWS", 10000), \
         patch("trend_discovery.config.TREND_MIN_LIKES", 1000), \
         patch("trend_discovery.config.TREND_TOP_N", 3):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert len(results) == 1
    assert results[0]["platform"] == "instagram"
    assert results[0]["post_id"] == "111222333"
    assert results[0]["views"] == 50000


def test_discover_instagram_returns_empty_on_login_failure():
    mock_cl = MagicMock()
    mock_cl.login.side_effect = Exception("Login failed")

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert results == []


def test_discover_instagram_filters_below_threshold():
    low_media = MagicMock()
    low_media.pk = 555
    low_media.code = "low"
    low_media.caption_text = "test"
    low_media.view_count = 100   # below TREND_MIN_VIEWS
    low_media.play_count = 0
    low_media.like_count = 10    # below TREND_MIN_LIKES

    mock_cl = MagicMock()
    mock_cl.user_id_from_username.return_value = 9999
    mock_cl.user_medias.return_value = [low_media]
    mock_cl.hashtag_medias_top.return_value = []

    with patch("trend_discovery.Client", return_value=mock_cl), \
         patch("trend_discovery.config.IG_USERNAME", "user"), \
         patch("trend_discovery.config.IG_PASSWORD", "pass"), \
         patch("trend_discovery.config.TREND_MIN_VIEWS", 10000), \
         patch("trend_discovery.config.TREND_MIN_LIKES", 1000), \
         patch("trend_discovery.config.TREND_TOP_N", 3):
        from trend_discovery import discover_instagram
        results = discover_instagram(["fashionpage"], [])

    assert results == []


def test_discover_tiktok_returns_empty_when_disabled():
    with patch("trend_discovery.config.TIKTOKAPI_ENABLED", False):
        from trend_discovery import discover_tiktok
        results = discover_tiktok(["user"], ["tag"])
    assert results == []


def test_discover_all_deduplicates_by_post_id():
    post_a = {
        "platform": "instagram", "post_id": "SAME", "url": "u", "caption": "",
        "views": 50000, "likes": 3000, "source": "a", "source_type": "account",
    }
    post_b = {
        "platform": "tiktok", "post_id": "SAME", "url": "u2", "caption": "",
        "views": 60000, "likes": 4000, "source": "b", "source_type": "hashtag",
    }

    with patch("trend_discovery.discover_instagram", return_value=[post_a]), \
         patch("trend_discovery.discover_tiktok", return_value=[post_b]), \
         patch("trend_discovery.config.TREND_ACCOUNTS_INSTAGRAM", []), \
         patch("trend_discovery.config.TREND_ACCOUNTS_TIKTOK", []), \
         patch("trend_discovery.config.TREND_HASHTAGS", []):
        from trend_discovery import discover_all
        results = discover_all()

    assert len(results) == 1
    assert results[0]["post_id"] == "SAME"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_discovery.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'trend_discovery'`

- [ ] **Step 3: Create trend_discovery.py**

Create `/Users/aegisen/fashion-bot/trend_discovery.py`:

```python
import logging

import config

log = logging.getLogger(__name__)


def _filter_posts(posts: list[dict]) -> list[dict]:
    qualifying = [
        p for p in posts
        if p["views"] >= config.TREND_MIN_VIEWS or p["likes"] >= config.TREND_MIN_LIKES
    ]
    return qualifying[: config.TREND_TOP_N]


def discover_instagram(accounts: list[str], hashtags: list[str]) -> list[dict]:
    try:
        from instagrapi import Client
    except ImportError:
        log.warning("instagrapi not installed, skipping Instagram discovery")
        return []

    cl = Client()
    try:
        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
    except Exception as e:
        log.warning("Instagram login failed: %s", e)
        return []

    results = []

    for username in accounts:
        try:
            uid = cl.user_id_from_username(username)
            medias = cl.user_medias(uid, amount=20)
            for m in medias:
                results.append({
                    "platform": "instagram",
                    "post_id": str(m.pk),
                    "url": f"https://www.instagram.com/p/{m.code}/",
                    "caption": m.caption_text or "",
                    "views": m.view_count or m.play_count or 0,
                    "likes": m.like_count or 0,
                    "source": username,
                    "source_type": "account",
                })
        except Exception as e:
            log.warning("Instagram account %s failed: %s", username, e)

    for tag in hashtags:
        try:
            medias = cl.hashtag_medias_top(tag, amount=20)
            for m in medias:
                results.append({
                    "platform": "instagram",
                    "post_id": str(m.pk),
                    "url": f"https://www.instagram.com/p/{m.code}/",
                    "caption": m.caption_text or "",
                    "views": m.view_count or m.play_count or 0,
                    "likes": m.like_count or 0,
                    "source": tag,
                    "source_type": "hashtag",
                })
        except Exception as e:
            log.warning("Instagram hashtag #%s failed: %s", tag, e)

    return _filter_posts(results)


def discover_tiktok(accounts: list[str], hashtags: list[str]) -> list[dict]:
    if not config.TIKTOKAPI_ENABLED:
        return []

    try:
        from TikTokApi import TikTokApi
        import asyncio
    except ImportError:
        log.warning("TikTokApi not installed, skipping TikTok discovery")
        return []

    async def _fetch() -> list[dict]:
        results = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(num_sessions=1, sleep_after=3)
                for username in accounts:
                    try:
                        async for video in api.user(username=username).videos(count=20):
                            d = video.as_dict
                            stats = d.get("stats", {})
                            results.append({
                                "platform": "tiktok",
                                "post_id": d["id"],
                                "url": f"https://www.tiktok.com/@{username}/video/{d['id']}",
                                "caption": d.get("desc", ""),
                                "views": stats.get("playCount", 0),
                                "likes": stats.get("diggCount", 0),
                                "source": username,
                                "source_type": "account",
                            })
                    except Exception as e:
                        log.warning("TikTok account %s failed: %s", username, e)
                for tag in hashtags:
                    try:
                        async for video in api.hashtag(name=tag).videos(count=20):
                            d = video.as_dict
                            stats = d.get("stats", {})
                            results.append({
                                "platform": "tiktok",
                                "post_id": d["id"],
                                "url": f"https://www.tiktok.com/tag/{tag}",
                                "caption": d.get("desc", ""),
                                "views": stats.get("playCount", 0),
                                "likes": stats.get("diggCount", 0),
                                "source": tag,
                                "source_type": "hashtag",
                            })
                    except Exception as e:
                        log.warning("TikTok hashtag #%s failed: %s", tag, e)
        except Exception as e:
            log.warning("TikTokApi session creation failed: %s", e)
        return results

    try:
        import asyncio
        raw = asyncio.run(_fetch())
    except Exception as e:
        log.warning("TikTok discovery failed: %s", e)
        return []

    return _filter_posts(raw)


def discover_all() -> list[dict]:
    ig_posts = discover_instagram(
        config.TREND_ACCOUNTS_INSTAGRAM,
        config.TREND_HASHTAGS,
    )
    tk_posts = discover_tiktok(
        config.TREND_ACCOUNTS_TIKTOK,
        config.TREND_HASHTAGS,
    )
    seen: set = set()
    result = []
    for p in ig_posts + tk_posts:
        if p["post_id"] not in seen:
            seen.add(p["post_id"])
            result.append(p)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_discovery.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add trend_discovery.py tests/test_trend_discovery.py
git commit -m "feat: add trend_discovery module for Instagram + TikTok viral post discovery"
```

---

## Task 5: trend_reshare.py + tests

**Files:**
- Create: `trend_reshare.py`
- Create: `tests/test_trend_reshare.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trend_reshare.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


FAKE_ITEM = {
    "itemName": "เสื้อยืด Korean Style",
    "priceDisplay": "299",
    "affiliateUrl": "https://s.shopee.co.th/abc",
    "itemId": "123",
    "imageUrl": "https://img.shopee.co.th/1.jpg",
    "sales": 500,
    "ratingStar": 4.5,
    "shopName": "KoreanFashion",
    "price": "299",
}

IG_POST = {
    "platform": "instagram",
    "post_id": "111222333",
    "url": "https://www.instagram.com/p/AbCdEf/",
    "caption": "ก่อนเจอ Shopee หลังเจอ Shopee 🔥 #แฟชั่น",
    "views": 50000,
    "likes": 3000,
    "source": "fashionpage",
    "source_type": "account",
}

TK_POST = {
    "platform": "tiktok",
    "post_id": "7123456789",
    "url": "https://www.tiktok.com/@user/video/7123456789",
    "caption": "POV: เจอเสื้อสวยราคาถูก 🥹",
    "views": 120000,
    "likes": 8000,
    "source": "tiktokfashion",
    "source_type": "account",
}


def test_find_shopee_match_returns_item_when_match_found():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="korean shirt")]

    with patch("trend_reshare.anthropic.Anthropic") as mock_cls, \
         patch("trend_reshare.search_products", return_value=[FAKE_ITEM]):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_msg
        mock_cls.return_value = mock_client

        from trend_reshare import find_shopee_match
        result = find_shopee_match(IG_POST)

    assert result is not None
    assert result["itemName"] == "เสื้อยืด Korean Style"


def test_find_shopee_match_returns_none_when_search_empty():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="dress")]

    with patch("trend_reshare.anthropic.Anthropic") as mock_cls, \
         patch("trend_reshare.search_products", return_value=[]):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_msg
        mock_cls.return_value = mock_client

        from trend_reshare import find_shopee_match
        result = find_shopee_match(TK_POST)

    assert result is None


def test_generate_affiliate_clip_picks_before_after_format(tmp_path):
    post = dict(IG_POST, caption="ก่อนเจอ Shopee หลังเจอ Shopee 🔥")
    fake_path = tmp_path / "trend_abc.mp4"
    fake_path.write_bytes(b"fake")

    with patch("trend_reshare.create_before_after_clip", return_value=fake_path) as mock_ba, \
         patch("trend_reshare.create_pov_meme_clip") as mock_pov, \
         patch("trend_reshare.create_price_shock_clip") as mock_ps, \
         patch("trend_reshare.create_beat_hook_clip") as mock_bh:
        from trend_reshare import generate_affiliate_clip
        result = generate_affiliate_clip(FAKE_ITEM, post)

    mock_ba.assert_called_once()
    mock_pov.assert_not_called()
    assert result == fake_path


def test_reshare_story_returns_false_on_instagrapi_error():
    mock_cl = MagicMock()
    mock_cl.login.side_effect = Exception("Auth failed")

    with patch("trend_reshare.Client", return_value=mock_cl), \
         patch("trend_reshare.config.IG_USERNAME", "user"), \
         patch("trend_reshare.config.IG_PASSWORD", "pass"):
        from trend_reshare import reshare_story
        result = reshare_story(IG_POST)

    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_reshare.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'trend_reshare'`

- [ ] **Step 3: Create trend_reshare.py**

Create `/Users/aegisen/fashion-bot/trend_reshare.py`:

```python
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

_CLIP_FORMAT_MAP = [
    (["ก่อน", "หลัง", "before", "after"], "before_after"),
    (["pov", "POV"], "pov_meme"),
    (["ราคา", "price", "shock", "แพง", "ถูก"], "price_shock"),
]


def reshare_story(post: dict) -> bool:
    if post["platform"] == "instagram":
        return _reshare_instagram_story(post)
    elif post["platform"] == "tiktok":
        return _repost_tiktok(post)
    return False


def _reshare_instagram_story(post: dict) -> bool:
    try:
        from instagrapi import Client
        cl = Client()
        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
        media_info = cl.media_info(int(post["post_id"]))
        thumb_url = str(media_info.thumbnail_url)
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


def _repost_tiktok(post: dict) -> bool:
    try:
        import json
        from playwright.sync_api import sync_playwright
        session_file = Path(config.TIKTOK_SESSION_FILE)
        if not session_file.exists():
            log.warning("No TikTok session, skipping repost")
            return False
        data = json.loads(session_file.read_text())
        cookies = data.get("cookies", [])
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.goto(post["url"], wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            share_btn = page.locator('[data-e2e="share-icon"]').first
            if share_btn.count() == 0:
                log.warning("TikTok share button not found for %s", post["post_id"])
                browser.close()
                return False
            share_btn.click()
            time.sleep(1)
            repost_btn = page.get_by_text("Repost", exact=False).first
            if repost_btn.count() == 0:
                log.warning("TikTok repost button not found for %s", post["post_id"])
                browser.close()
                return False
            repost_btn.click()
            time.sleep(2)
            browser.close()
        log.info("TikTok repost: %s", post["post_id"])
        return True
    except Exception as e:
        log.warning("TikTok repost failed: %s", e)
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
        query = msg.content[0].text.strip()
    except Exception as e:
        log.warning("Claude keyword extraction failed: %s", e)
        return None
    if not query:
        return None
    results = search_products(query)
    return results[0] if results else None


def generate_affiliate_clip(item: dict, post: dict) -> Path:
    caption_lower = post.get("caption", "").lower()
    clip_type = "beat_hook"
    for keywords, ctype in _CLIP_FORMAT_MAP:
        if any(kw.lower() in caption_lower for kw in keywords):
            clip_type = ctype
            break
    output_name = f"trend_{post['post_id'][:20]}"
    if clip_type == "before_after":
        return create_before_after_clip(item, output_name)
    elif clip_type == "pov_meme":
        return create_pov_meme_clip(item, output_name)
    elif clip_type == "price_shock":
        return create_price_shock_clip(item, output_name)
    else:
        return create_beat_hook_clip(item, output_name)


def post_affiliate_clip(clip_path: Path, item: dict) -> None:
    from content_gen import generate_video_caption
    from tiktok import post_clip
    from youtube import post_short
    caption_data = generate_video_caption(item)
    caption = caption_data["caption"]
    title = item["itemName"][:100]
    try:
        post_clip(clip_path, caption)
        log.info("TikTok affiliate posted: %s", item["itemName"][:40])
    except Exception as e:
        log.error("TikTok affiliate post failed: %s", e)
    try:
        post_short(clip_path, title, caption)
        log.info("YouTube affiliate posted: %s", item["itemName"][:40])
    except Exception as e:
        log.error("YouTube affiliate post failed: %s", e)
    try:
        from instagram import post_reel_clip
        post_reel_clip(clip_path, caption)
        log.info("Instagram affiliate posted: %s", item["itemName"][:40])
    except Exception as e:
        log.error("Instagram affiliate post failed: %s", e)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_trend_reshare.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add trend_reshare.py tests/test_trend_reshare.py
git commit -m "feat: add trend_reshare module for story reshare, Shopee matching, and affiliate clip posting"
```

---

## Task 6: content_gen.py — extra_hooks param

**Files:**
- Modify: `content_gen.py`

- [ ] **Step 1: Update generate_video_caption signature and prompt**

In `content_gen.py`, replace `def generate_video_caption(item: dict) -> dict:` and its prompt construction with:

```python
def generate_video_caption(item: dict, extra_hooks: list = None) -> dict:
    """Generate TikTok-native caption: scroll-stop hook + body + CTA + hashtags."""
    price = item.get("priceDisplay") or item.get("priceMin") or item.get("price", "")
    if isinstance(price, (int, float)) and price > 1000:
        price_display = f"฿{float(price)/100000:.0f}"
    else:
        price_display = str(price) if price else ""

    rating = float(item.get("ratingStar") or 0)
    try:
        price_num = float(str(price_display).replace("฿", "").replace(",", ""))
    except ValueError:
        price_num = 999

    if price_num < 300:
        formula = "PRICE_SHOCK"
    elif rating >= 4.8:
        formula = "SOCIAL_PROOF"
    else:
        formula = "POV"

    import random as _random
    if _random.random() < 0.3:
        formula = "MEME"

    formula_guide = {
        "PRICE_SHOCK": f"Hook: แค่ {price_display} บาท?! (price shock, stops scroll)",
        "SOCIAL_PROOF": f"Hook: ⭐{rating}/5 คนรีวิวเยอะมาก (social proof hook)",
        "POV": f"Hook: POV: เจอเสื้อผ้าน่ารักราคา {price_display} บาทใน Shopee 🥹",
        "MEME": "Hook: เพื่อน: แต่งตัวดีขึ้นได้ยังไง? / ฉัน: (show product) 😅 (relatable meme format)",
    }[formula]

    hooks_section = ""
    if extra_hooks:
        hooks_section = "\nTrending hooks from viral posts (consider adapting one of these):\n" + "\n".join(
            f"- {h}" for h in extra_hooks[:3]
        )

    prompt = f"""You are a viral Thai TikTok fashion creator for @trendyinthai.

Product: {item['itemName']}
Price: {price_display}
Rating: {rating} stars
Formula: {formula_guide}{hooks_section}

Write a TikTok caption (Thai-primary):

LINE 1 — HOOK (CRITICAL): Must stop the scroll. Under 50 Thai characters. Use the formula above. One emoji.
LINE 2-3 — BODY: 1-2 lines. Product benefit, why it's worth it. Casual TikTok voice.
LINE 4 — CTA: "กดลิ้งค์ด้านล่างได้เลย 👇" or "ลิ้งค์ด้านล่าง 🛒"

Rules:
- Thai only (light English OK as flair, not a full section)
- Hook line must be standalone — someone reading only line 1 must feel curious or shocked
- Sound like a real Thai TikTok creator, not an ad
- NO fake urgency like "เหลือแค่ 3 ชิ้น"
- Total: 4-5 lines max

Return ONLY the caption text."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()

    hashtags = " ".join(HASHTAGS_TIKTOK)
    affiliate_url = item.get("affiliateUrl", "")
    link_line = f"\n{affiliate_url}" if affiliate_url else ""
    full_caption = f"{caption_body}\n\n{hashtags}{link_line}"

    return {
        "caption": full_caption,
        "caption_body": caption_body,
        "hashtags": hashtags,
    }
```

- [ ] **Step 2: Run full test suite to verify nothing broke**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/ --ignore=tests/test_tiktok.py -q
```

Expected: all tests pass (no new failures)

- [ ] **Step 3: Commit**

```bash
git add content_gen.py
git commit -m "feat: generate_video_caption accepts optional extra_hooks from trend signals"
```

---

## Task 7: main.py — run_trend_cycle + biased run_video_cycle

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add imports to main.py**

At the top of `main.py`, after the existing imports, add:

```python
from trend_discovery import discover_all
from trend_reshare import reshare_story, find_shopee_match, generate_affiliate_clip, post_affiliate_clip
from trend_signals import extract_signals, save_signals, load_signals
from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY, TREND_RESHARE_ENABLED
```

Note: replace the existing `from config import POSTS_PER_DAY, REELS_PER_DAY, IMAGE_POSTS_PER_DAY, CLIPS_PER_DAY` line (it currently doesn't import `TREND_RESHARE_ENABLED`).

- [ ] **Step 2: Add run_trend_cycle() function**

Add this function after `run_video_cycle` and before `_parse_script`:

```python
def run_trend_cycle():
    log.info("Starting trend cycle")

    posts = discover_all()
    if not posts:
        log.info("No viral posts found, skipping trend cycle")
        return

    for post in posts:
        try:
            if TREND_RESHARE_ENABLED:
                reshare_story(post)
            item = find_shopee_match(post)
            if item:
                clip = generate_affiliate_clip(item, post)
                post_affiliate_clip(clip, item)
        except Exception as e:
            log.error("Trend post %s failed: %s", post["post_id"], e)

    signals = extract_signals(posts)
    save_signals(signals)
    log.info("Trend cycle done: %d posts processed", len(posts))
```

- [ ] **Step 3: Update run_video_cycle to read trend signals**

In `run_video_cycle`, add at the very start of the function body (before the `log.info` call or right after it):

```python
    signals = load_signals()
    trending_hooks = signals.get("hooks", [])
```

Replace:
```python
    CLIP_TYPES = [
        "multi", "price_reveal", "countdown",
        "before_after", "pov_meme", "price_shock", "beat_hook",
    ]
```

with:
```python
    CLIP_TYPES = [
        "multi", "price_reveal", "countdown",
        "before_after", "pov_meme", "price_shock", "beat_hook",
    ]
    # Append trending types once each to increase their probability
    CLIP_TYPES = CLIP_TYPES + signals.get("top_clip_types", [])
```

Replace the line:
```python
            caption_data = generate_video_caption(item)
```

with:
```python
            caption_data = generate_video_caption(item, extra_hooks=trending_hooks or None)
```

- [ ] **Step 4: Add run_trend_cycle to __main__ block**

Replace:
```python
if __name__ == "__main__":
    run_post_cycle()
    run_video_cycle()
```

with:
```python
if __name__ == "__main__":
    run_post_cycle()
    run_video_cycle()
    run_trend_cycle()
```

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/ --ignore=tests/test_tiktok.py -q
```

Expected: all tests pass

- [ ] **Step 6: Smoke test imports**

```bash
cd /Users/aegisen/fashion-bot && TREND_RESHARE_ENABLED=false TIKTOKAPI_ENABLED=false python -c "
import main
print('run_trend_cycle:', callable(main.run_trend_cycle))
print('Imports OK')
"
```

Expected:
```
run_trend_cycle: True
Imports OK
```

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat: add run_trend_cycle, wire trend signals into run_video_cycle clip biasing"
```

---

## Self-Review

**Spec coverage:**
- ✅ `discover_instagram` + `discover_tiktok` — Task 4
- ✅ `discover_all` dedup — Task 4
- ✅ `reshare_story` Instagram + TikTok — Task 5
- ✅ `find_shopee_match` Claude + search — Task 5
- ✅ `generate_affiliate_clip` format inference — Task 5
- ✅ `post_affiliate_clip` all platforms — Task 5
- ✅ `extract_signals` hooks + clip types + hashtags — Task 3
- ✅ `save_signals` / `load_signals` — Task 3
- ✅ `search_products` — Task 2
- ✅ `generate_video_caption(extra_hooks)` — Task 6
- ✅ `run_trend_cycle` — Task 7
- ✅ `run_video_cycle` biasing — Task 7
- ✅ Config vars — Task 1
- ✅ Graceful degradation (TikTokApi import fail, login fail, no match) — Tasks 4, 5

**Type consistency:** `post_dict` schema defined in Task 4 and used consistently in Tasks 5, 7. `search_products` returns same item dict format as `get_trending_fashion`. `generate_affiliate_clip` calls the same `viral_gen` functions as `run_video_cycle`.

**No placeholders found.**
