import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    RPC_URL = os.getenv("RPC_URL", "https://rpc.ankr.com/solana")
    ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))