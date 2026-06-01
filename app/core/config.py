from dotenv import load_dotenv
import os

load_dotenv()

# WhatsApp Configuration
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")

# Vehicle API Configuration
VEHICLE_API_BASE_URL = os.getenv("VEHICLE_API_BASE_URL", "https://gtrac.in:8089/trackingdashboard")
VEHICLE_API_USERNAME = os.getenv("VEHICLE_API_USERNAME")
VEHICLE_API_PASSWORD = os.getenv("VEHICLE_API_PASSWORD")
VEHICLE_API_TIMEOUT = int(os.getenv("VEHICLE_API_TIMEOUT", "30"))
VEHICLE_API_MAX_RETRIES = int(os.getenv("VEHICLE_API_MAX_RETRIES", "3"))
VEHICLE_API_RETRY_DELAY = float(os.getenv("VEHICLE_API_RETRY_DELAY", "1.0"))

# Redis Configuration (Optional)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
VEHICLE_CACHE_TTL = int(os.getenv("VEHICLE_CACHE_TTL", "300"))  # 5 minutes
