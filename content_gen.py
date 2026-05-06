import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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


def generate_caption(item: dict, post_type: str = "image") -> dict:
    """Generate bilingual Thai+EN caption with CTA and hashtags."""
    price = item.get("priceDisplay") or item.get("priceMin") or item.get("price", "")
    if isinstance(price, (int, float)) and price > 1000:
        price_display = f"฿{float(price)/100000:.0f}"
    else:
        price_display = str(price) if price else "ราคาพิเศษ"

    prompt = f"""You are a Thai fashion influencer content creator for Instagram @trendyinthai.

Product: {item['itemName']}
Price: {price_display}
Shop: {item.get('shopName', '')}
Rating: {item.get('ratingStar', '')} stars
Post type: {post_type}

Write an Instagram caption in TWO sections:
1. Thai section (2-3 sentences): Exciting, trendy, FOMO-inducing. Mention price if good deal. End with call-to-action to click link in bio.
2. English section (2-3 sentences): Same energy, translated naturally (not word-for-word).

Rules:
- Thai first, then English
- Use emojis naturally
- Sound like real influencer, not ad
- CTA: "ลิ้งค์ใน bio + ซื้อได้ที่ Shopee 👆" (Thai) and "Shop on Shopee — link in bio 👆" (English)
- Keep under 200 words total
- NO fake urgency like "only 3 left"

Return ONLY the caption text, no labels."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()

    top_hashtags = " ".join(HASHTAGS_TH[:6] + HASHTAGS_EN[:5])
    full_caption = f"{caption_body}\n\n{top_hashtags}"

    return {
        "caption": full_caption,
        "caption_body": caption_body,
        "hashtags": top_hashtags,
    }


def generate_reel_script(items: list[dict]) -> str:
    """Generate short script/text overlays for 5-sec reel featuring multiple items."""
    names = [item["itemName"][:40] for item in items[:3]]
    prompt = f"""Create text overlays for a 5-second Instagram Reel showing trending Shopee Thailand fashion.
Items: {', '.join(names)}

Return exactly 3 text overlays (one per second range):
Line 1 (0-1.5s): Hook in Thai (max 8 words)
Line 2 (1.5-3.5s): Product highlight Thai+EN (max 10 words)
Line 3 (3.5-5s): CTA in Thai (max 6 words) + 👆

Format:
HOOK: <text>
HIGHLIGHT: <text>
CTA: <text>"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
