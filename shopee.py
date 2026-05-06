"""
Fetch trending fashion from Lazada TH — public, no login required.
Reuses one Playwright browser across all keyword searches.
"""
import os
import time
from playwright.sync_api import sync_playwright

LAZADA_SEARCH = "https://www.lazada.co.th/catalog/?q={}&sort=popularity&page=1"

FASHION_KEYWORDS = [
    "เสื้อผ้าผู้หญิง",
    "ชุดเดรส",
    "เสื้อผ้าเกาหลี",
    "เสื้อครอป",
    "ชุดเซต",
]

SHOPEE_AFF_ID = os.getenv("SHOPEE_AFFILIATE_ID", "27191763")

_EXTRACT_JS = """() => {
    const cards = document.querySelectorAll('[data-tracking="product-card"]');
    return Array.from(cards).map(c => {
        const img = c.querySelector('img');
        const link = c.querySelector('a');
        const name = c.querySelector('.RfADt');
        const price = c.querySelector('.ooOxS');
        let imgUrl = img ? (img.getAttribute('data-src') || img.getAttribute('src') || '') : '';
        if (imgUrl.startsWith('data:')) imgUrl = '';
        return {
            name: name ? name.textContent.trim() : '',
            image: imgUrl,
            url: link ? link.href : '',
            price: price ? price.textContent.trim() : '',
        };
    }).filter(i => i.name && i.image);
}"""


def _scrape_page(page, keyword: str, limit: int) -> list[dict]:
    encoded = keyword.replace(" ", "+")
    page.goto(LAZADA_SEARCH.format(encoded), wait_until="load", timeout=45000)
    time.sleep(3)
    raw = page.evaluate(_EXTRACT_JS) or []
    items = []
    for r in raw[:limit]:
        parsed = _parse(r)
        if parsed:
            items.append(parsed)
    return items


def _parse(raw: dict):
    name = raw.get("name", "")
    if not name:
        return None
    image = raw.get("image", "")
    if image.startswith("//"):
        image = "https:" + image
    url = raw.get("url", "")
    if url and not url.startswith("http"):
        url = "https://www.lazada.co.th" + url
    item_id = url.split("/")[-1].split(".")[0] if url else name[:20]
    price_str = raw.get("price", "ราคาพิเศษ")
    return {
        "itemId": item_id,
        "itemName": name[:80],
        "price": price_str,
        "priceDisplay": price_str,
        "imageUrl": image,
        "shopName": "",
        "ratingStar": 0,
        "sales": 0,
        "productUrl": url,
        "affiliateUrl": f"{url}{'&' if '?' in url else '?'}laz_aff={SHOPEE_AFF_ID}",
    }


def get_trending_fashion(limit_per_keyword: int = 8) -> list[dict]:
    seen = set()
    all_items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="th-TH",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = ctx.new_page()
        for keyword in FASHION_KEYWORDS:
            try:
                items = _scrape_page(page, keyword, limit_per_keyword)
                for item in items:
                    if item["itemId"] not in seen and item["imageUrl"]:
                        seen.add(item["itemId"])
                        all_items.append(item)
                print(f"  '{keyword}': {len(items)} items")
            except Exception as e:
                print(f"  Warning '{keyword}': {e}")
        browser.close()
    return all_items


def pick_top_items(items: list[dict], n: int = 5) -> list[dict]:
    return items[:n]
