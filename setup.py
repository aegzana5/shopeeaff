"""
Auto-setup: fetches IG Business Account ID from token and writes to .env.
Run once before first use.
"""
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

IG_API_BASE = "https://graph.facebook.com/v19.0"
TOKEN = os.getenv("IG_ACCESS_TOKEN")


def fetch_ig_account_id() -> str:
    resp = requests.get(
        f"{IG_API_BASE}/me/accounts",
        params={"access_token": TOKEN, "fields": "instagram_business_account,name"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    for page in data.get("data", []):
        ig = page.get("instagram_business_account")
        if ig:
            print(f"Found IG Business Account: {ig['id']} (Page: {page['name']})")
            return ig["id"]
    raise RuntimeError("No Instagram Business Account linked to this token. Connect IG to Facebook Page in Meta Business Suite.")


def write_env_value(key: str, value: str):
    env_path = ".env"
    with open(env_path, "r") as f:
        content = f.read()
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={value}\n"
    with open(env_path, "w") as f:
        f.write(content)
    print(f"✓ {key} written to .env")


def run():
    print("=== Fashion Bot Auto Setup ===\n")

    missing = []
    if not TOKEN or "FILL" in (TOKEN or ""):
        missing.append("IG_ACCESS_TOKEN")
    if not os.getenv("ANTHROPIC_API_KEY") or "FILL" in (os.getenv("ANTHROPIC_API_KEY") or ""):
        missing.append("ANTHROPIC_API_KEY")

    if missing:
        print(f"⚠ Still need in .env: {', '.join(missing)}")
        return

    account_id = os.getenv("IG_BUSINESS_ACCOUNT_ID", "")
    if not account_id or "FILL" in account_id:
        print("Fetching IG Business Account ID...")
        account_id = fetch_ig_account_id()
        write_env_value("IG_BUSINESS_ACCOUNT_ID", account_id)
    else:
        print(f"✓ IG_BUSINESS_ACCOUNT_ID already set: {account_id}")

    print("\n✅ Setup complete. Run: python main.py")


if __name__ == "__main__":
    run()
