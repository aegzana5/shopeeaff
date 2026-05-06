import os
from dotenv import load_dotenv

load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SHOPEE_FEED_URL = os.getenv("SHOPEE_FEED_URL")
if not SHOPEE_FEED_URL:
    raise EnvironmentError("SHOPEE_FEED_URL is required. Set it in .env")
SHOPEE_FEED_CACHE_HOURS = int(os.getenv("SHOPEE_FEED_CACHE_HOURS", "6"))

POST_TIMES = os.getenv(
    "POST_TIMES",
    "08:00,09:30,11:00,12:30,14:00,15:30,17:00,18:30,20:00,21:30",
).split(",")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Bangkok")

FASHION_KEYWORDS = [
    "เสื้อผ้าผู้หญิง",
    "เสื้อผ้าแฟชั่น",
    "ชุดเดรส",
    "เสื้อครอป",
    "กางเกงยีนส์ผู้หญิง",
    "ชุดเซต",
    "เสื้อผ้าเกาหลี",
]

POSTS_PER_DAY = 10
REELS_PER_DAY = 0
IMAGE_POSTS_PER_DAY = 10
CLIPS_PER_DAY = int(os.getenv("CLIPS_PER_DAY", "3"))
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "assets/youtube_token.json")
YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "assets/youtube_client_secrets.json")
TIKTOK_SESSION_FILE = os.getenv("TIKTOK_SESSION_FILE", "assets/tiktok_session.json")
