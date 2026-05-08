import logging
import requests
from pathlib import Path
import config

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("assets/output")
_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def generate_voiceover_from_text(text: str, output_name: str) -> "Path | None":
    """Generate TTS from arbitrary text."""
    if not config.TTS_ENABLED or not config.ELEVENLABS_API_KEY:
        return None
    url = _TTS_URL.format(voice_id=config.ELEVENLABS_VOICE_ID)
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text[:500],
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        out_path = OUTPUT_DIR / f"{output_name}_vo.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return out_path
    except Exception as e:
        log.warning("ElevenLabs TTS failed: %s", e)
        return None


def generate_voiceover(item: dict, output_name: str) -> "Path | None":
    if not config.TTS_ENABLED or not config.ELEVENLABS_API_KEY:
        return None

    price = item.get("priceDisplay") or item.get("price", "")
    name = item["itemName"][:60]
    script = f"{name} ราคาแค่ {price} บาท\nลิ้งค์ด้านล่างได้เลย"

    url = _TTS_URL.format(voice_id=config.ELEVENLABS_VOICE_ID)
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        out_path = OUTPUT_DIR / f"{output_name}_vo.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return out_path
    except Exception as e:
        log.warning("ElevenLabs TTS failed: %s", e)
        return None
