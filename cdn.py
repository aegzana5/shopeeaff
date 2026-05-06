"""
Upload local files to free public CDN.
Uses 0x0.st — no account, no API key, files persist 24h+ (enough for IG processing).
"""
import requests
from pathlib import Path


def upload(file_path: Path) -> str:
    """Upload file, return public URL."""
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://0x0.st",
            files={"file": (file_path.name, f)},
            timeout=60,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"Upload failed: {url}")
    return url
