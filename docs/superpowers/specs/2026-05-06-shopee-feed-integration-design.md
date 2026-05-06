# Shopee Affiliate Feed Integration

**Date:** 2026-05-06
**Account:** @trendyinthai
**Affiliate ID:** 15317630400

## Goal

Replace Lazada scraper with Shopee affiliate product feed. Bot fetches pre-built affiliate links from Shopee's datafeed API, filters for fashion items, and posts to Instagram with Shopee-specific hashtags.

## Architecture

Single source pipeline — Shopee feed only. No Lazada fallback.

```
Shopee Feed API (TSV)
  └─→ shopee.py: download + cache + parse + filter
        └─→ main.py: pick_top_items → create_post_image → post_image
```

## Files Changed

| File | Action |
|------|--------|
| `shopee.py` | Rewritten — feed-based, replaces Lazada Playwright scraper |
| `config.py` | Replace `SHOPEE_AFFILIATE_ID` with `SHOPEE_FEED_URL` + `SHOPEE_FEED_CACHE_HOURS=6` |
| `content_gen.py` | Replace hashtags with Shopee-specific sets |
| `main.py` | Update imports, remove Lazada references |
| `shopee_login.py` | Deleted |
| `setup.py` | Deleted |
| `cdn.py` | Deleted |
| `media_gen.py` | Unchanged |
| `instagram.py` | Unchanged |
| `scheduler.py` | Unchanged |
| `setup_instagram.py` | Unchanged |

## shopee.py — Feed Module

**Responsibilities:**
1. GET feed URL from `config.SHOPEE_FEED_URL`
2. Cache response to `assets/shopee_feed.tsv`; skip download if file age < `SHOPEE_FEED_CACHE_HOURS`
3. Parse TSV: extract `item_id`, `item_name`, `price`, `image_url`, `affiliate_url`, `category`
4. Filter: keep rows where category matches fashion keywords (clothing, shoes, bags, accessories, เสื้อผ้า, กระเป๋า, รองเท้า)
5. Return list of dicts matching existing item shape

**Item dict shape (unchanged from previous):**
```python
{
    "itemId": str,
    "itemName": str,          # truncated to 80 chars
    "price": str,
    "priceDisplay": str,
    "imageUrl": str,
    "affiliateUrl": str,      # pre-built by Shopee, no manual construction
    "shopName": str,
    "ratingStar": float,
    "sales": int,
}
```

**`pick_top_items(items, n)`** — unchanged signature, sorts by sales desc.

## content_gen.py — Hashtags

Replace current Lazada/generic hashtags:

```python
HASHTAGS_TH = [
    "#Shopeeไทย", "#ช้อปปี้", "#ช้อปปี้ไทยแลนด์",
    "#แฟชั่นShopee", "#ของดีในShopee", "#แฟชั่นไทย",
    "#เทรนด์แฟชั่น", "#ไอเดียแต่งตัว",
]
HASHTAGS_EN = [
    "#ShopeeTH", "#ShopeeThailand", "#ShopeeAffiliate",
    "#ThailandFashion", "#KoreanFashion", "#OOTDThailand",
    "#AsianFashion", "#StreetStyleBangkok",
]
```

Prompt text updated: references "Shopee Thailand" instead of "Shopee TH" / "ชอปปี้ไทยแลนด์".

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Feed download fails | Log error, skip cycle |
| Feed has 0 fashion items after filter | Log + skip cycle |
| Individual item image download fails | Skip item, continue with remaining |
| IG session expired | Existing behavior unchanged — raises RuntimeError |

No stale-cache fallback beyond TTL — stale data risks outdated prices/sold-out items.

## config.py Changes

```python
# Remove:
SHOPEE_AFFILIATE_ID = os.getenv("SHOPEE_AFFILIATE_ID", "27191763")

# Add:
SHOPEE_FEED_URL = os.getenv("SHOPEE_FEED_URL")  # required, no default
SHOPEE_FEED_CACHE_HOURS = int(os.getenv("SHOPEE_FEED_CACHE_HOURS", "6"))
```

`.env` updated with `SHOPEE_FEED_URL=<feed_url>`.

## Success Criteria

- `python main.py` completes a post cycle using Shopee feed items
- Affiliate links in posted captions contain valid Shopee affiliate tracking
- Cache file created at `assets/shopee_feed.tsv`, reused within 6h window
- No references to Lazada remain in codebase
