"""
Find complementary Shopee products to complete an outfit.
Uses Claude to determine what to search, then Shopee to find matches.
"""
import logging
import anthropic
import config
from shopee import search_products

log = logging.getLogger(__name__)


def find_outfit_matches(item: dict, n: int = 2) -> list:
    """Return up to n complementary Shopee products for the given item."""
    name = item.get("itemName", "")
    if not name:
        return []
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{
                "role": "user",
                "content": (
                    f"Thai fashion product: {name[:100]}\n\n"
                    f"List exactly {n} complementary product types to complete a full outfit "
                    "(shoes, bag, hat, pants, top, accessories, etc. — whatever matches this item best).\n"
                    "Return ONE Thai Shopee search term per line only. No numbering, no explanation.\n"
                    "Examples: กางเกงขาบาน / รองเท้าส้นสูง / กระเป๋าสะพาย / หมวกบักเก็ต"
                ),
            }],
        )
        queries = [q.strip() for q in msg.content[0].text.strip().splitlines() if q.strip()]
    except Exception as e:
        log.warning("Claude outfit query failed: %s", e)
        return []

    matches = []
    seen = {str(item.get("itemId", ""))}
    for query in queries[:n + 1]:
        try:
            results = search_products(query)
            for r in results:
                rid = str(r.get("itemId", ""))
                if rid not in seen and r.get("affiliateUrl"):
                    matches.append(r)
                    seen.add(rid)
                    break
        except Exception as e:
            log.warning("Shopee search '%s' failed: %s", query, e)
        if len(matches) >= n:
            break

    return matches[:n]
