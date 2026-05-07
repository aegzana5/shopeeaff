import json
import time
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Minimal CSV fixture — matches real feed structure
# Note: comma-separated, utf-8-sig BOM, 'product_short link' has a space
SAMPLE_CSV = (
    "﻿image_link,image_link_2,itemid,title,sale_price,price,"
    "product_short link,global_category1,global_category2,global_category3,"
    "shop_name,item_rating,item_sold\n"
    "https://img.example.com/1.jpg,,111,เสื้อยืดสีขาว,299,350,"
    "https://s.shopee.co.th/aff1,เสื้อผ้าผู้หญิง,เสื้อยืด,,Shop A,4.8,500\n"
    "https://img.example.com/2.jpg,,222,โทรศัพท์,5999,6500,"
    "https://s.shopee.co.th/aff2,โทรศัพท์,,,Shop B,4.5,200\n"
)


def _make_cache(tmp_path, items, age_seconds=0):
    f = tmp_path / "shopee_cache.json"
    f.write_text(json.dumps(items))
    if age_seconds > 0:
        old_time = time.time() - age_seconds
        import os
        os.utime(f, (old_time, old_time))
    return f


def test_parse_feed_returns_fashion_items_only():
    from shopee import _parse_feed
    items = _parse_feed(io.StringIO(SAMPLE_CSV))
    assert len(items) == 1
    assert items[0]["itemId"] == "111"


def test_item_dict_has_required_keys():
    from shopee import _parse_feed
    items = _parse_feed(io.StringIO(SAMPLE_CSV))
    required = {"itemId", "itemName", "price", "priceDisplay", "imageUrl",
                "affiliateUrl", "shopName", "ratingStar", "sales"}
    assert required.issubset(items[0].keys())


def test_sale_price_used_as_display():
    from shopee import _parse_feed
    items = _parse_feed(io.StringIO(SAMPLE_CSV))
    assert items[0]["priceDisplay"] == "299"


def test_affiliate_url_from_product_short_link():
    from shopee import _parse_feed
    items = _parse_feed(io.StringIO(SAMPLE_CSV))
    assert items[0]["affiliateUrl"] == "https://s.shopee.co.th/aff1"


def test_cache_used_when_fresh(tmp_path, monkeypatch):
    cached = [{"itemId": "1", "itemName": "test"}]
    cache_path = _make_cache(tmp_path, cached, age_seconds=100)
    monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
    monkeypatch.setattr("shopee.CACHE_HOURS", 6)

    mock_get = MagicMock()
    with patch("shopee.requests.get", mock_get):
        import importlib, shopee
        importlib.reload(shopee)
        monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
        monkeypatch.setattr("shopee.CACHE_HOURS", 6)
        result = shopee.get_trending_fashion()
    mock_get.assert_not_called()
    assert result == cached


def test_cache_refreshed_when_stale(tmp_path, monkeypatch):
    old_cache = [{"itemId": "old"}]
    cache_path = _make_cache(tmp_path, old_cache, age_seconds=7 * 3600)
    monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
    monkeypatch.setattr("shopee.CACHE_HOURS", 6)

    # Simulate resp.raw as a bytes stream readable by TextIOWrapper
    raw_bytes = SAMPLE_CSV.encode("utf-8")
    mock_raw = io.BytesIO(raw_bytes)
    mock_resp = MagicMock()
    mock_resp.raw = mock_raw

    with patch("shopee.requests.get", return_value=mock_resp):
        import importlib, shopee as shopee_mod
        importlib.reload(shopee_mod)
        monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
        monkeypatch.setattr("shopee.CACHE_HOURS", 6)
        result = shopee_mod.get_trending_fashion()

    # Verify fresh data returned (fashion item from feed), not stale cache
    assert any(i["itemId"] == "111" for i in result)


def test_download_failure_returns_stale_cache(tmp_path, monkeypatch):
    stale_items = [{"itemId": "stale", "itemName": "old item"}]
    cache_path = _make_cache(tmp_path, stale_items, age_seconds=7 * 3600)
    monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
    monkeypatch.setattr("shopee.CACHE_HOURS", 6)

    with patch("shopee.requests.get", side_effect=ConnectionError("network down")):
        import importlib, shopee as shopee_mod
        importlib.reload(shopee_mod)
        monkeypatch.setattr("shopee.CACHE_PATH", cache_path)
        monkeypatch.setattr("shopee.CACHE_HOURS", 6)
        result = shopee_mod.get_trending_fashion()

    assert result == stale_items


def test_pick_top_items_returns_n():
    from shopee import pick_top_items
    items = [{"sales": i, "itemId": str(i)} for i in range(10)]
    result = pick_top_items(items, n=3)
    assert len(result) == 3


def test_pick_top_items_sorts_by_sales_desc():
    from shopee import pick_top_items
    items = [{"sales": 10}, {"sales": 50}, {"sales": 5}]
    result = pick_top_items(items, n=2)
    assert result[0]["sales"] == 50


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
