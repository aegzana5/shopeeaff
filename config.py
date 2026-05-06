import os
from dotenv import load_dotenv

load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

SHOPEE_AFFILIATE_ID = os.getenv("SHOPEE_AFFILIATE_ID", "27191763")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

POST_TIMES = os.getenv("POST_TIMES", "08:00,11:00,14:00,18:00,21:00").split(",")
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

POSTS_PER_DAY = 5
REELS_PER_DAY = 2
IMAGE_POSTS_PER_DAY = 3
