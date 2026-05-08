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

HASHTAGS_TIKTOK = [
    "#แฟชั่นราคาถูก", "#เสื้อผ้าน่ารัก", "#ไอเดียแต่งตัว",
    "#ของดีในShopee", "#ถูกมาก", "#แฟชั่นไทย",
    "#fyp", "#ShopeeTH", "#ช้อปปี้ไทย",
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
    affiliate_url = item.get("affiliateUrl", "")
    link_line = f"\n🛒 {affiliate_url}" if affiliate_url else ""
    full_caption = f"{caption_body}\n\n{top_hashtags}{link_line}"

    return {
        "caption": full_caption,
        "caption_body": caption_body,
        "hashtags": top_hashtags,
    }


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

    prompt = f"""You are a viral Thai TikTok fashion creator. Write captions that sound exactly like a real person posting, not a brand or ad.

Product: {item['itemName']}
Price: {price_display} บาท
Rating: {rating} stars
Hook formula: {formula_guide}{hooks_section}

Caption rules:
- LINE 1: Hook only. Short, punchy, creates curiosity or shock. Under 40 chars. Use the formula.
- LINE 2-3: Why this product slaps. Casual, like texting a friend. Max 2 lines.
- LINE 4: "ลิ้งค์ใน bio นะ 🔗" (always this exact CTA — link is in bio)
- Hashtags: DO NOT include — added separately

Tone: Real Thai gen-z creator. Drop filler words. No corporate speak. No "สินค้าคุณภาพดี".
Viral examples of LINE 1:
- "แค่ {price_display} บาท?? ฉันซื้อผิดหรือเปล่า 😭"
- "POV: เจอชุดนี้ใน Shopee ตอนตีสอง 🌙"
- "เพื่อนถามว่าซื้อที่ไหน ฉันไม่บอก 🤫"
- "ราคานี้ดีเกินจริง ฉันว่ามันผิดพลาด"

Return ONLY the caption (4 lines, no hashtags)."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()

    hashtags = " ".join(HASHTAGS_TIKTOK)
    full_caption = f"{caption_body}\n\n{hashtags}"

    return {
        "caption": full_caption,
        "caption_body": caption_body,
        "hashtags": hashtags,
        "affiliate_url": item.get("affiliateUrl", ""),
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
