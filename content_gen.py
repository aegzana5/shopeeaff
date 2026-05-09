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

HASHTAGS_IG_TH = [
    "#แฟชั่น", "#เสื้อผ้าผู้หญิง", "#ของถูก", "#ลดราคา", "#shopee",
    "#แฟชั่นราคาถูก", "#สไตล์เกาหลี", "#ชุดเซ็ต", "#เสื้อผ้าออนไลน์", "#ootd",
    "#แฟชั่นไทย", "#เทรนด์แฟชั่น", "#ไอเดียแต่งตัว", "#ของดีในShopee",
    "#เสื้อผ้าน่ารัก", "#แฟชั่นออนไลน์", "#ช้อปออนไลน์", "#Shopeeไทย",
    "#ลุคน่ารัก", "#สไตล์ไทย",
]


def generate_caption(item: dict, post_type: str = "image") -> dict:
    """Generate Thai-only Instagram caption: hook / benefit / price / CTA."""
    price = item.get("priceDisplay") or item.get("priceMin") or item.get("price", "")
    if isinstance(price, (int, float)) and price > 1000:
        price_display = f"฿{float(price)/100000:.0f}"
    else:
        price_display = str(price) if price else "ราคาพิเศษ"

    prompt = f"""คุณเป็น content creator แฟชั่นไทยที่เขียน caption ยาวๆ แบบ YouTube — อธิบายสินค้าละเอียด มีข้อมูลจริง ช่วยคนตัดสินใจซื้อ

สินค้า: {item['itemName']}
ราคา: {price_display} บาท
คะแนน: {item.get('ratingStar', '')} ดาว ({item.get('ratingCount', '')} รีวิว)
ยอดขาย: {item.get('sold', '')}

เขียน caption ภาษาไทยอย่างเดียว โครงสร้าง:

บรรทัดแรก: ประโยคเด็ด ดึงดูดความสนใจ ใช้ emoji (เหมือน YouTube thumbnail title)

[เว้นบรรทัด]

อธิบายสินค้า 4-6 บรรทัด:
- สินค้านี้คืออะไร ใส่โอกาสไหน เหมาะกับใคร
- วัสดุ / ผ้า / ฟีเจอร์เด่น (ถ้าอนุมานได้จากชื่อ)
- ทำไมคนชอบ / รีวิวดี / ขายดี
- แมทช์กับอะไรได้บ้าง
ใช้ emoji ประจำแต่ละบรรทัด แต่พอประมาณ

[เว้นบรรทัด]

💰 ราคา {price_display} บาท (บอก value — ถูกหรือคุ้มยังไง)

[เว้นบรรทัด]

🛒 ช้อปได้เลยที่ลิ้งค์ใน bio หรือคอมเมนต์ "สนใจ" แล้วจะส่งลิ้งค์ให้

ห้าม: hashtag, ภาษาอังกฤษ (ยกเว้นชื่อแบรนด์), คำโฆษณาทั่วไป เช่น "สินค้าคุณภาพ"
เขียนเหมือนคนจริงๆ ไม่ใช่ bot"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()
    hashtags = " ".join(HASHTAGS_IG_TH)

    return {
        "caption": caption_body,
        "caption_body": caption_body,
        "hashtags": hashtags,
    }


def generate_video_caption(item: dict, extra_hooks: list = None) -> dict:
    """Generate hook-style caption for Instagram Reels: scroll-stop hook + body + CTA."""
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
- LINE 4: "🛒 ลิ้งค์ด้านล่าง" (CTA pointing to link in description)
- Hashtags: DO NOT include — added separately

Tone: Real Thai gen-z creator. Drop filler words. No corporate speak. No "สินค้าคุณภาพดี".
Viral examples of LINE 1:
- "แค่ {price_display} บาท?? ฉันซื้อผิดหรือเปล่า 😭"
- "POV: เจอชุดนี้ใน Shopee ตอนตีสอง 🌙"
- "เพื่อนถามว่าซื้อที่ไหน ฉันไม่บอก 🤫"
- "ราคานี้ดีเกินจริง ฉันว่ามันผิดพลาด"
- "ลิ้งค์ด้านล่างได้เลย 🛒"

Return ONLY the caption (4 lines, no hashtags)."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()

    return {
        "caption": caption_body,
        "caption_body": caption_body,
        "hashtags": " ".join(HASHTAGS_IG_TH),
        "affiliate_url": item.get("affiliateUrl", ""),
    }


def generate_outfit_caption(main_item: dict, matches: list) -> dict:
    """Generate outfit combination caption for all items."""
    def fmt_price(it):
        p = it.get("priceDisplay") or it.get("priceMin") or it.get("price", "")
        if isinstance(p, (int, float)) and p > 1000:
            return f"฿{float(p)/100000:.0f}"
        return str(p) if p else ""

    items_block = "\n".join(
        f"- {it['itemName'][:40]} {fmt_price(it)}"
        for it in [main_item] + matches
    )

    prompt = f"""Viral Thai TikTok outfit combo caption. Showing a complete outfit.

Items:
{items_block}

Rules:
- LINE 1: Short scroll-stop hook about the outfit combo (Thai, under 40 chars)
- LINE 2-3: Why this combo slaps, casual Thai gen-z tone, like texting a friend
- LINE 4: "ลิ้งค์ใน bio นะ 🔗"
- No hashtags, no corporate speak
- Sound like someone who just discovered the perfect affordable outfit

Return ONLY the caption (4 lines)."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=280,
        messages=[{"role": "user", "content": prompt}],
    )
    caption_body = message.content[0].text.strip()
    hashtags = " ".join(HASHTAGS_TIKTOK)

    link_lines = "\n".join(
        f"🛒 {it['itemName'][:25]}: {it['affiliateUrl']}"
        for it in [main_item] + matches
        if it.get("affiliateUrl")
    )
    full_caption = f"{caption_body}\n\n{hashtags}"

    return {
        "caption": full_caption,
        "caption_body": caption_body,
        "caption_with_links": f"{full_caption}\n{link_lines}" if link_lines else full_caption,
        "hashtags": hashtags,
        "affiliate_urls": {it["itemName"][:25]: it.get("affiliateUrl", "") for it in [main_item] + matches},
    }


def generate_first_comment(item: dict) -> str:
    """Return hashtag block for first comment: base HASHTAGS_IG_TH + item keyword tags."""
    import re
    name = item.get("itemName", "")
    words = re.split(r'[\s/\-,。、]+', name)
    dynamic: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) >= 3 and not w.isdigit():
            tag = f"#{w.replace(' ', '')}"
            if tag not in dynamic and tag not in HASHTAGS_IG_TH:
                dynamic.append(tag)
        if len(dynamic) >= 5:
            break

    return " ".join(HASHTAGS_IG_TH[:15] + dynamic)


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
