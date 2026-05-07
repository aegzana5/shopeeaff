import logging

import config

log = logging.getLogger(__name__)

try:
    from instagrapi import Client
except ImportError:
    Client = None  # type: ignore[assignment,misc]


def _filter_posts(posts: list[dict]) -> list[dict]:
    qualifying = [
        p for p in posts
        if p["views"] >= config.TREND_MIN_VIEWS or p["likes"] >= config.TREND_MIN_LIKES
    ]
    return qualifying[: config.TREND_TOP_N]


def discover_instagram(accounts: list[str], hashtags: list[str]) -> list[dict]:
    if Client is None:
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
