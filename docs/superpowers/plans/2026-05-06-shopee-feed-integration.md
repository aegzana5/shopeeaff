# Shopee Feed Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Lazada Playwright scraper with Shopee affiliate product feed, updating hashtags and removing obsolete files.

**Architecture:** `shopee.py` is rewritten to download a TSV product feed from the Shopee affiliate API, cache it locally for 6 hours, filter for fashion items, and return dicts with the same shape the rest of the pipeline already expects. `config.py` swaps the old affiliate ID for the feed URL. `content_gen.py` gets Shopee-specific hashtags. Three stale files are deleted.

**Tech Stack:** Python 3, `requests`, `csv` (stdlib), `pathlib`, `pytest`

**Prerequisites:** `pytest` not in `requirements.txt` — add it before Task 2:
```bash
echo "pytest>=8.0.0" >> /Users/aegisen/fashion-bot/requirements.txt
pip install pytest
mkdir -p /Users/aegisen/fashion-bot/tests
```

---

### Task 0: Inspect Shopee Feed Columns

**Files:**
- Read: `.env` (for feed URL)

- [ ] **Step 1: Download feed and inspect headers**

```bash
python3 - <<'EOF'
import os, requests, csv, io
from dotenv import load_dotenv
load_dotenv()
url = os.getenv("SHOPEE_FEED_URL")
r = requests.get(url, timeout=30)
r.raise_for_status()
# Print first 3 rows to see column names and values
reader = csv.DictReader(io.StringIO(r.text), delimiter='\t')
for i, row in enumerate(reader):
    if i == 0:
        print("COLUMNS:", list(row.keys()))
    if i < 3:
        print(f"ROW {i}:", dict(row))
    else:
        break
EOF
```

- [ ] **Step 2: Note column names**

Record exact column names for: item ID, item name, price, image URL, affiliate link, category, shop name, rating, sales. These go into `shopee.py` column mappings in Task 2.

---

### Task 1: Update `config.py`

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Replace Shopee affiliate ID with feed URL**

Replace the existing `config.py` content with:

```python
import os
from dotenv import load_dotenv

load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SHOPEE_FEED_URL = os.getenv("SHOPEE_FEED_URL")
SHOPEE_FEED_CACHE_HOURS = int(os.getenv("SHOPEE_FEED_CACHE_HOURS", "6"))

POST_TIMES = os.getenv("POST_TIMES", "08:00,11:00,14:00,18:00,21:00").split(",")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Bangkok")

FASHION_KEYWORDS = [
    "เสื้อผ้าผู้หญิง",
    "เสื้อผ้าแฟชั่น",
    "ชุดเดรส",
    "เสื้อครอป",
    "กางเกงยีนส์ผู้หญิง",
    "ชุดเซต",
    "เสื้อผ้าเกาหลี",
]

POSTS_PER_DAY = 5
REELS_PER_DAY = 2
IMAGE_POSTS_PER_DAY = 3
```

- [ ] **Step 2: Update `.env` with feed URL**

Add to `.env` (replacing any existing `SHOPEE_AFFILIATE_ID` line):

```
SHOPEE_FEED_URL=https://affiliate.shopee.co.th/api/v1/datafeed/download?id=YWJjZGVmZ2hpamtsbW5vcHBN5NpCWc_cJAzlYyIJ5ucFaO3p-Cmchoc8YmumCd5T
```

- [ ] **Step 3: Update `.env.example`**

Replace `SHOPEE_AFFILIATE_ID=` line with:

```
SHOPEE_FEED_URL=https://affiliate.shopee.co.th/api/v1/datafeed/download?id=YOUR_FEED_ID
SHOPEE_FEED_CACHE_HOURS=6
```

- [ ] **Step 4: Commit**

```bash
git add config.py .env.example
git commit -m "config: replace Shopee affiliate ID with feed URL"
```

---

### Task 2: Rewrite `shopee.py` as Feed Client

**Files:**
- Modify: `shopee.py`
- Create: `tests/test_shopee.py`

**Note:** Use exact column names discovered in Task 0. The template below uses placeholder names — replace with real ones.

- [ ] **Step 1: Write failing tests**

Create `tests/test_shopee.py`:

```python
import csv
import io
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# --- Minimal TSV fixture with two rows ---
SAMPLE_TSV = """item_id\titem_name\tprice\timage_url\taffiliate_link\tcategory\tshop_name\trating_star\tsales
111\tเสื้อยืดสีขาว\t299\thttps://img.example.com/1.jpg\thttps://s.shopee.co.th/aff1\tเสื้อผ้าผู้หญิง\tShop A\t4.8\t500
222\tโทรศัพท์มือถือ\t5999\thttps://img.example.com/2.jpg\thttps://s.shopee.co.th/aff2\tโทรศัพท์\tShop B\t4.5\t200
"""

# IMPORTANT: Replace column name strings above with exact names from Task 0.


def _make_feed(tmp_path, content=SAMPLE_TSV, age_seconds=0):
    """Write a fake cached feed file."""
    f = tmp_path / "shopee_feed.tsv"
    f.write_text(content)
    if age_seconds > 0:
        old_time = time.time() - age_seconds
        import os
        os.utime(f, (old_time, old_time))
    return f


def test_parse_returns_fashion_items_only(tmp_path):
    from shopee import _parse_feed
    items = _parse_feed(SAMPLE_TSV)
    assert len(items) == 1
    assert items[0]["itemId"] == "111"
    assert items[0]["itemName"] == "เสื้อยืดสีขาว"
    assert items[0]["affiliateUrl"] == "https://s.shopee.co.th/aff1"


def test_item_dict_has_required_keys(tmp_path):
    from shopee import _parse_feed
    items = _parse_feed(SAMPLE_TSV)
    required = {"itemId", "itemName", "price", "priceDisplay", "imageUrl",
                "affiliateUrl", "shopName", "ratingStar", "sales"}
    assert required.issubset(items[0].keys())


def test_cache_used_when_fresh(tmp_path, monkeypatch):
    feed_path = _make_feed(tmp_path, age_seconds=100)
    monkeypatch.setattr("shopee.CACHE_PATH", feed_path)
    monkeypatch.setattr("shopee.CACHE_HOURS", 6)
    mock_get = MagicMock()
    with patch("shopee.requests.get", mock_get):
        from shopee import get_trending_fashion
        get_trending_fashion()
    mock_get.assert_not_called()


def test_cache_refreshed_when_stale(tmp_path, monkeypatch):
    feed_path = _make_feed(tmp_path, age_seconds=7 * 3600)
    monkeypatch.setattr("shopee.CACHE_PATH", feed_path)
    monkeypatch.setattr("shopee.CACHE_HOURS", 6)
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_TSV
    with patch("shopee.requests.get", return_value=mock_resp) as mock_get:
        from shopee import get_trending_fashion
        get_trending_fashion()
    mock_get.assert_called_once()


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
    assert result[1]["sales"] == 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_shopee.py -v 2>&1 | head -40
```

Expected: ImportError or AttributeError — `_parse_feed` not defined yet.

- [ ] **Step 3: Rewrite `shopee.py`**

Replace entire `shopee.py` with:

```python
import csv
import io
import time
from pathlib import Path

import requests

from config import SHOPEE_FEED_URL, SHOPEE_FEED_CACHE_HOURS

CACHE_PATH = Path("assets/shopee_feed.tsv")
CACHE_HOURS = SHOPEE_FEED_CACHE_HOURS

# Fashion category substrings (Thai + English). Case-insensitive match.
_FASHION_CATS = [
    "เสื้อผ้า", "แฟชั่น", "ชุด", "กางเกง", "กระโปรง", "เสื้อ",
    "รองเท้า", "กระเป๋า", "เครื่องประดับ", "accessories",
    "fashion", "clothing", "shoes", "bag", "dress",
]

# --- Column name mapping: update keys to match Task 0 findings ---
_COL = {
    "id":        "item_id",          # product ID
    "name":      "item_name",        # product name
    "price":     "price",            # price (string, e.g. "299" or "฿299")
    "image":     "image_url",        # product image URL
    "affiliate": "affiliate_link",   # pre-built affiliate URL
    "category":  "category",         # category string
    "shop":      "shop_name",        # seller name
    "rating":    "rating_star",      # float string
    "sales":     "sales",            # int string
}


def _is_fresh() -> bool:
    if not CACHE_PATH.exists():
        return False
    age = time.time() - CACHE_PATH.stat().st_mtime
    return age < CACHE_HOURS * 3600


def _download() -> str:
    resp = requests.get(SHOPEE_FEED_URL, timeout=60)
    resp.raise_for_status()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(resp.text, encoding="utf-8")
    return resp.text


def _load() -> str:
    if _is_fresh():
        return CACHE_PATH.read_text(encoding="utf-8")
    return _download()


def _is_fashion(category: str) -> bool:
    cat_lower = category.lower()
    return any(kw in cat_lower for kw in _FASHION_CATS)


def _parse_row(row: dict) -> dict | None:
    name = row.get(_COL["name"], "").strip()
    category = row.get(_COL["category"], "")
    image = row.get(_COL["image"], "").strip()
    affiliate = row.get(_COL["affiliate"], "").strip()

    if not name or not image or not affiliate:
        return None
    if not _is_fashion(category):
        return None

    price_raw = row.get(_COL["price"], "").strip()
    try:
        sales = int(row.get(_COL["sales"], "0").strip() or "0")
    except ValueError:
        sales = 0
    try:
        rating = float(row.get(_COL["rating"], "0").strip() or "0")
    except ValueError:
        rating = 0.0

    if image.startswith("//"):
        image = "https:" + image

    return {
        "itemId":      row.get(_COL["id"], name[:20]).strip(),
        "itemName":    name[:80],
        "price":       price_raw,
        "priceDisplay": price_raw,
        "imageUrl":    image,
        "affiliateUrl": affiliate,
        "shopName":    row.get(_COL["shop"], "").strip(),
        "ratingStar":  rating,
        "sales":       sales,
    }


def _parse_feed(tsv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    items = []
    seen = set()
    for row in reader:
        parsed = _parse_row(row)
        if parsed and parsed["itemId"] not in seen:
            seen.add(parsed["itemId"])
            items.append(parsed)
    return items


def get_trending_fashion(limit_per_keyword: int = 8) -> list[dict]:
    tsv = _load()
    return _parse_feed(tsv)


def pick_top_items(items: list[dict], n: int = 5) -> list[dict]:
    return sorted(items, key=lambda x: x["sales"], reverse=True)[:n]
```

- [ ] **Step 4: Update column names in `_COL`**

Using exact column names from Task 0, update the `_COL` dict values in `shopee.py`. Also update `SAMPLE_TSV` header in `tests/test_shopee.py` to match real columns.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/test_shopee.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add shopee.py tests/test_shopee.py
git commit -m "feat: rewrite shopee.py as affiliate feed client"
```

---

### Task 3: Update Hashtags in `content_gen.py`

**Files:**
- Modify: `content_gen.py`

- [ ] **Step 1: Replace hashtag lists**

In `content_gen.py`, replace the `HASHTAGS_TH` and `HASHTAGS_EN` lists:

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

- [ ] **Step 2: Update prompt text**

In `generate_caption`, change the prompt line:

```python
# Old:
    shop_name = item.get('shopName', '')
# (inside prompt f-string) "Shop: {item.get('shopName', '')}"

# Change the platform reference in the prompt from:
    prompt = f"""You are a Thai fashion influencer content creator for Instagram @trendyinthai.
# to: (no change needed — just update the CTA line below)
```

In the same prompt, update the CTA instructions:

```python
# Replace:
- CTA: "ลิ้งค์ในไบโอ 👆" (Thai) and "Link in bio 👆" (English)
# With:
- CTA: "ลิ้งค์ใน bio + ซื้อได้ที่ Shopee 👆" (Thai) and "Shop on Shopee — link in bio 👆" (English)
```

- [ ] **Step 3: Verify no import errors**

```bash
cd /Users/aegisen/fashion-bot && python -c "from content_gen import generate_caption; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add content_gen.py
git commit -m "feat: update hashtags and CTA to Shopee branding"
```

---

### Task 4: Update `main.py` Imports

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Remove Lazada reference**

In `main.py`, `get_trending_fashion` and `pick_top_items` already come from `shopee` — no import change needed. But verify the import line is:

```python
from shopee import get_trending_fashion, pick_top_items
```

If it says anything else (e.g. references to `lazada`), fix it to the line above.

- [ ] **Step 2: Verify run cycle imports cleanly**

```bash
cd /Users/aegisen/fashion-bot && python -c "from main import run_post_cycle; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "chore: verify main.py uses shopee feed imports"
```

---

### Task 5: Delete Obsolete Files

**Files:**
- Delete: `shopee_login.py`, `setup.py`, `cdn.py`

- [ ] **Step 1: Confirm nothing imports them**

```bash
cd /Users/aegisen/fashion-bot && grep -r "shopee_login\|from setup import\|import cdn\|from cdn" --include="*.py" .
```

Expected: no output (nothing imports these).

- [ ] **Step 2: Delete files**

```bash
rm /Users/aegisen/fashion-bot/shopee_login.py \
   /Users/aegisen/fashion-bot/setup.py \
   /Users/aegisen/fashion-bot/cdn.py
```

- [ ] **Step 3: Commit**

```bash
git add -u
git commit -m "chore: remove obsolete shopee_login, setup, cdn files"
```

---

### Task 6: End-to-End Smoke Test

**Files:** none (manual verification)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/aegisen/fashion-bot && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Dry-run feed fetch**

```bash
cd /Users/aegisen/fashion-bot && python3 - <<'EOF'
from shopee import get_trending_fashion, pick_top_items
items = get_trending_fashion()
print(f"Total fashion items from feed: {len(items)}")
top = pick_top_items(items, n=5)
for i in top:
    print(f"  {i['itemName'][:50]} | {i['priceDisplay']} | {i['affiliateUrl'][:60]}")
EOF
```

Expected: prints 5 items with valid Shopee affiliate URLs (containing `shopee.co.th`).

- [ ] **Step 3: Verify cache file created**

```bash
ls -lh /Users/aegisen/fashion-bot/assets/shopee_feed.tsv
```

Expected: file exists, non-zero size.

- [ ] **Step 4: Verify no Lazada references remain**

```bash
grep -r "lazada\|laz_aff\|SHOPEE_AFFILIATE_ID" --include="*.py" /Users/aegisen/fashion-bot/
```

Expected: no output.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: verified Shopee feed integration end-to-end"
```
