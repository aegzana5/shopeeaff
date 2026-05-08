"""
AI image generation for fashion products.
Photoroom: background removal
fal.ai FLUX: Thai model lifestyle generation
remove.bg: fallback bg removal
"""
import logging
import os
import requests
from pathlib import Path

import config

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("assets/output")

PHOTOROOM_SEGMENT_URL = "https://sdk.photoroom.com/v1/segment"
REMOVEBG_URL = "https://api.remove.bg/v1.0/removebg"
FAL_MODEL = "fal-ai/flux/schnell"


def remove_bg(image_url: str, output_name: str) -> "Path | None":
    """Remove product background. Tries Photoroom then remove.bg."""
    api_key = getattr(config, "PHOTOROOM_API_KEY", "")
    if api_key:
        result = _photoroom_remove_bg(image_url, output_name, api_key)
        if result:
            return result
    api_key2 = getattr(config, "REMOVEBG_API_KEY", "")
    if api_key2:
        return _removebg(image_url, output_name, api_key2)
    return None


def _photoroom_remove_bg(image_url: str, output_name: str, api_key: str) -> "Path | None":
    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        resp = requests.post(
            PHOTOROOM_SEGMENT_URL,
            headers={"x-api-key": api_key},
            files={"image_file": ("product.jpg", img_resp.content, "image/jpeg")},
            timeout=30,
        )
        resp.raise_for_status()
        out = OUTPUT_DIR / f"{output_name}_nobg.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.content)
        return out
    except Exception as e:
        log.warning("Photoroom bg removal failed: %s", e)
        return None


def _removebg(image_url: str, output_name: str, api_key: str) -> "Path | None":
    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        resp = requests.post(
            REMOVEBG_URL,
            headers={"X-Api-Key": api_key},
            files={"image_file": ("product.jpg", img_resp.content, "image/jpeg")},
            data={"size": "auto"},
            timeout=30,
        )
        resp.raise_for_status()
        out = OUTPUT_DIR / f"{output_name}_nobg.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.content)
        return out
    except Exception as e:
        log.warning("remove.bg failed: %s", e)
        return None


def generate_model_image(item: dict, output_name: str) -> "Path | None":
    """Generate Thai model wearing product via fal.ai FLUX schnell."""
    api_key = getattr(config, "FAL_API_KEY", "")
    if not api_key:
        return None
    try:
        import fal_client  # type: ignore
        os.environ.setdefault("FAL_KEY", api_key)

        name = item.get("itemName", "")[:80]
        prompt = (
            f"Professional Thai fashion model wearing {name}, "
            "Bangkok street style, modern Asian aesthetic, "
            "clean white studio background, natural warm lighting, "
            "high quality fashion photography, TikTok/Instagram editorial style, "
            "full body shot showing outfit clearly"
        )
        result = fal_client.run(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "image_size": "portrait_4_3",
                "num_inference_steps": 4,
                "num_images": 1,
            },
        )
        img_url = result["images"][0]["url"]
        resp = requests.get(img_url, timeout=60)
        resp.raise_for_status()
        out = OUTPUT_DIR / f"{output_name}_model.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.content)
        return out
    except ImportError:
        log.warning("fal-client not installed: pip install fal-client")
        return None
    except Exception as e:
        log.warning("fal.ai model generation failed: %s", e)
        return None
