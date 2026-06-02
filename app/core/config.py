from dotenv import load_dotenv
import os

load_dotenv()

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")

GTRAC_BASE_URL = os.getenv("GTRAC_BASE_URL")
GTRAC_API_KEY = os.getenv("GTRAC_API_KEY")