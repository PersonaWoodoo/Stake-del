import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK")
ORDERS_CHANNEL_ID = int(os.getenv("ORDERS_CHANNEL_ID"))
STARS_PER_ATTEMPT = int(os.getenv("STARS_PER_ATTEMPT", "5"))
REFS_PER_ATTEMPT = int(os.getenv("REFS_PER_ATTEMPT", "10"))
START_ATTEMPTS = int(os.getenv("START_ATTEMPTS", "1"))
PRIVACY_URL = os.getenv("PRIVACY_URL")
RULES_URL = os.getenv("RULES_URL")
