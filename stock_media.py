import logging
import re
import requests
from pathlib import Path
import config

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("assets/output")

_PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

_THAI_TO_EN = {
    "เสื้อ": "shirt",
    "เสื้อยืด": "tshirt",
    "กางเกง": "pants",
    "กระโปรง": "skirt",
    "ชุด": "dress",
    "เดรส": "dress",
    "รองเท้า": "shoes",
    "กระเป๋า": "bag",
    "แจ็คเก็ต": "jacket",
    "บลาวส์": "blouse",
    "แฟชั่น": "fashion",
    "เกาหลี": "korean",
    "ญี่ปุ่น": "japanese",
    "สาว": "girl",
}


def _extract_keywords(item_name: str) -> list:
    keywords = []
    for thai, en in _THAI_TO_EN.items():
        if thai in item_name and en not in keywords:
            keywords.append(en)
    en_words = re.findall(r"[A-Za-z]{3,}", item_name)
    for w in en_words[:2]:
        if w.lower() not in keywords:
            keywords.append(w)
    return (keywords or ["fashion"])[:3]


def fetch_bg_video(keywords: list, output_name: str) -> "Path | None":
    if not config.STOCK_MEDIA_ENABLED or not config.PEXELS_API_KEY:
        return None

    query = "fashion " + " ".join(keywords[:3])
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": 5,
        "size": "medium",
    }

    try:
        resp = requests.get(_PEXELS_VIDEO_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            return None

        video_files = sorted(
            videos[0]["video_files"],
            key=lambda x: x.get("height", 0),
            reverse=True,
        )
        video_url = video_files[0]["link"]

        out_path = OUTPUT_DIR / f"{output_name}_bg.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        dl = requests.get(video_url, stream=True, timeout=60)
        dl.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in dl.iter_content(chunk_size=8192):
                f.write(chunk)
        return out_path
    except Exception as e:
        log.warning("Pexels fetch failed: %s", e)
        return None


def generate_bg_image(item: dict, output_name: str) -> "Path | None":
    if not config.STOCK_MEDIA_ENABLED or not config.REPLICATE_API_TOKEN:
        return None

    keywords = _extract_keywords(item["itemName"])
    prompt = (
        f"fashion lifestyle {' '.join(keywords)} Bangkok street aesthetic "
        "bokeh soft light vibrant colors, vertical portrait 9:16"
    )

    try:
        import replicate
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={"prompt": prompt, "width": 768, "height": 1344, "num_outputs": 1},
        )
        img_url = str(output[0])
        resp = requests.get(img_url, timeout=30)
        resp.raise_for_status()
        out_path = OUTPUT_DIR / f"{output_name}_bg.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return out_path
    except Exception as e:
        log.warning("Replicate SD failed: %s", e)
        return None
