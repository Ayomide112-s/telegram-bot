import json
import os
import base58
import base64
import logging
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from mnemonic import Mnemonic
from config import Config

# ================= LOGGER =================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= SOLANA CLIENT =================
client = Client("https://api.mainnet-beta.solana.com")
mnemo = Mnemonic("english")

# ================= FILE STORAGE =================
WALLET_FILE = "backend/wallets.json"


def load_wallet_file():
    """Load all wallets from file."""
    if not os.path.exists(WALLET_FILE):
        return {}
    try:
        with open(WALLET_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load wallet file: {e}")
        return {}


def save_wallet_file(data):
    """Save all wallets to file."""
    try:
        os.makedirs(os.path.dirname(WALLET_FILE), exist_ok=True)
        with open(WALLET_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save wallet file: {e}")


# ================= WALLET GENERATION =================
def generate_wallet(user_id):
    """
    Generate a new wallet with a 12-word mnemonic.
    Stores private key and phrase in wallet file.
    Returns pubkey, private_key (base58), phrase.
    """
    try:
        phrase = mnemo.generate(strength=128)
        seed = mnemo.to_seed(phrase)
        seed_bytes = seed[:32]
        wallet = Keypair.from_seed(seed_bytes)
        private_key = base58.b58encode(bytes(wallet)).decode()

        data = load_wallet_file()
        data[str(user_id)] = {
            "private_key": private_key,
            "phrase": phrase
        }
        save_wallet_file(data)

        return wallet.pubkey(), private_key, phrase
    except Exception as e:
        logger.error(f"Wallet generation failed for user {user_id}: {e}")
        return None, None, None


# ================= IMPORT WALLET =================
def import_private_key(user_id, private_key):
    """
    Import wallet using a base58-encoded private key.
    Returns public key if successful, None otherwise.
    """
    try:
        decoded = base58.b58decode(private_key)
        wallet = Keypair.from_bytes(decoded)

        data = load_wallet_file()
        data[str(user_id)] = {
            "private_key": private_key,
            "phrase": None
        }
        save_wallet_file(data)

        return wallet.pubkey()
    except Exception as e:
        logger.error(f"Failed to import PK for user {user_id}: {e}")
        return None


def import_phrase(user_id, phrase):
    """
    Import wallet using a mnemonic seed phrase.
    Returns public key if successful, None otherwise.
    """
    try:
        seed = mnemo.to_seed(phrase)
        seed_bytes = seed[:32]
        wallet = Keypair.from_seed(seed_bytes)
        private_key = base58.b58encode(bytes(wallet)).decode()

        data = load_wallet_file()
        data[str(user_id)] = {
            "private_key": private_key,
            "phrase": phrase
        }
        save_wallet_file(data)

        return wallet.pubkey()
    except Exception as e:
        logger.error(f"Failed to import phrase for user {user_id}: {e}")
        return None


# ================= LOAD WALLET =================
def load_wallet(user_id):
    """Load Keypair object from stored wallet."""
    data = load_wallet_file()
    user = data.get(str(user_id))
    if not user:
        return None
    try:
        decoded = base58.b58decode(user["private_key"])
        return Keypair.from_bytes(decoded)
    except Exception as e:
        logger.error(f"Failed to load wallet for user {user_id}: {e}")
        return None


def get_wallet_data(user_id):
    """Return stored private_key and phrase for user."""
    data = load_wallet_file()
    return data.get(str(user_id))


# ================= BALANCE =================
def get_balance(user_id):
    """
    Return SOL balance of user's wallet.
    Returns 0 if wallet not found or RPC fails.
    """
    wallet = load_wallet(user_id)
    if not wallet:
        return 0
    try:
        balance = client.get_balance(wallet.pubkey())
        return balance['result']['value'] / 1e9
    except Exception as e:
        logger.error(f"Failed to fetch balance for user {user_id}: {e}")
        return 0


# ================= SIGN & SEND =================
def sign_and_send(user_id, tx_base64):
    """
    Sign a base64-encoded VersionedTransaction and send it.
    Returns transaction signature or None on failure.
    """
    wallet = load_wallet(user_id)
    if not wallet:
        logger.error(f"No wallet found for user {user_id} to sign transaction.")
        return None

    try:
        tx_bytes = base64.b64decode(tx_base64)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        tx.sign([wallet])
        response = client.send_transaction(tx)
        return response['result'] if 'result' in response else response
    except Exception as e:
        logger.error(f"Failed to sign/send transaction for user {user_id}: {e}")
        return None
