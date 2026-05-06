"""
Fetch trending fashion from Shopee affiliate product feed.
Streams the 3.94 GB CSV feed, filters fashion items on the fly,
and caches up to 500 results as assets/shopee_cache.json.
"""
import csv
import io
import json
import time
from pathlib import Path
from typing import Optional

import requests

from config import SHOPEE_FEED_URL, SHOPEE_FEED_CACHE_HOURS

CACHE_PATH = Path("assets/shopee_cache.json")
CACHE_HOURS = SHOPEE_FEED_CACHE_HOURS
MAX_ITEMS = 500  # collect up to 500 fashion items from the 19.6M-row feed

_FASHION_CATS = [
    "เสื้อผ้า", "แฟชั่น", "ชุด", "กางเกง", "กระโปรง", "เสื้อ",
    "รองเท้า", "กระเป๋า", "เครื่องประดับ",
    "fashion", "clothing", "shoes", "bag", "dress", "accessories",
]


def _is_fashion(row: dict) -> bool:
    cats = (
        row.get("global_category1", "") +
        row.get("global_category2", "") +
        row.get("global_category3", "")
    ).lower()
    if cats:
        return any(kw in cats for kw in _FASHION_CATS)
    # Fallback: check title if categories are empty
    title = row.get("title", "").lower()
    return any(kw in title for kw in _FASHION_CATS)


def _parse_row(row: dict) -> Optional[dict]:
    name = row.get("title", "").strip()
    image = row.get("image_link", "").strip()
    affiliate = row.get("product_short link", "").strip()  # space in column name

    if not name or not image or not affiliate:
        return None

    price_display = row.get("sale_price", "").strip() or row.get("price", "").strip()
    try:
        sales = int(row.get("item_sold", "0").strip() or "0")
    except ValueError:
        sales = 0
    try:
        rating = float(row.get("item_rating", "0").strip() or "0")
    except ValueError:
        rating = 0.0

    if image.startswith("//"):
        image = "https:" + image

    return {
        "itemId": row.get("itemid", name[:20]).strip(),
        "itemName": name[:80],
        "price": price_display,
        "priceDisplay": price_display,
        "imageUrl": image,
        "affiliateUrl": affiliate,
        "shopName": row.get("shop_name", "").strip(),
        "ratingStar": rating,
        "sales": sales,
    }


def _parse_feed(lines) -> list[dict]:
    """Parse fashion items from an iterable of CSV text lines."""
    reader = csv.DictReader(lines)
    # Strip BOM from first fieldname if present
    if reader.fieldnames and reader.fieldnames[0].startswith("﻿"):
        reader.fieldnames[0] = reader.fieldnames[0].lstrip("﻿")
    items = []
    seen = set()
    for row in reader:
        if len(items) >= MAX_ITEMS:
            break
        if not _is_fashion(row):
            continue
        parsed = _parse_row(row)
        if parsed and parsed["itemId"] not in seen:
            seen.add(parsed["itemId"])
            items.append(parsed)
    return items


def _is_fresh() -> bool:
    if not CACHE_PATH.exists():
        return False
    return (time.time() - CACHE_PATH.stat().st_mtime) < CACHE_HOURS * 3600


def _fetch_and_parse() -> list[dict]:
    resp = requests.get(SHOPEE_FEED_URL, stream=True, timeout=(10, 300))
    resp.raise_for_status()
    stream = io.TextIOWrapper(resp.raw, encoding="utf-8-sig")
    items = _parse_feed(stream)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(items), encoding="utf-8")
    tmp.replace(CACHE_PATH)
    return items


def get_trending_fashion() -> list[dict]:
    if _is_fresh():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    try:
        return _fetch_and_parse()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Shopee feed fetch failed: %s", e)
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return []


def pick_top_items(items: list[dict], n: int = 5) -> list[dict]:
    return sorted(items, key=lambda x: x["sales"], reverse=True)[:n]
