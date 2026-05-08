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
TIKTOK_ENABLED = os.getenv("TIKTOK_ENABLED", "true").lower() == "true"

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
PHOTOROOM_API_KEY = os.getenv("PHOTOROOM_API_KEY", "")
REMOVEBG_API_KEY = os.getenv("REMOVEBG_API_KEY", "")
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
OUTFIT_MATCHES = int(os.getenv("OUTFIT_MATCHES", "2"))
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
STOCK_MEDIA_ENABLED = os.getenv("STOCK_MEDIA_ENABLED", "true").lower() == "true"

TREND_ACCOUNTS_INSTAGRAM = [a for a in os.getenv("TREND_ACCOUNTS_INSTAGRAM", "").split(",") if a]
TREND_ACCOUNTS_TIKTOK    = [a for a in os.getenv("TREND_ACCOUNTS_TIKTOK", "").split(",") if a]
TREND_HASHTAGS           = [h for h in os.getenv("TREND_HASHTAGS", "แฟชั่น,ootdthailand,shopee_th").split(",") if h]
TREND_MIN_VIEWS          = int(os.getenv("TREND_MIN_VIEWS", "10000"))
TREND_MIN_LIKES          = int(os.getenv("TREND_MIN_LIKES", "1000"))
TREND_TOP_N              = int(os.getenv("TREND_TOP_N", "3"))
TREND_RESHARE_ENABLED    = os.getenv("TREND_RESHARE_ENABLED", "true").lower() == "true"
TIKTOKAPI_ENABLED        = os.getenv("TIKTOKAPI_ENABLED", "true").lower() == "true"
IG_SESSION_FILE          = os.getenv("IG_SESSION_FILE", "assets/ig_session.json")
