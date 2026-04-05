import json
import os
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from mnemonic import Mnemonic
import base58
import base64
from config import Config

client = Client(Config.RPC_URL)
mnemo = Mnemonic("english")

WALLET_FILE = "backend/wallets.json"


# ================= FILE =================
def load_wallet_file():
    if not os.path.exists(WALLET_FILE):
        return {}
    with open(WALLET_FILE, "r") as f:
        return json.load(f)


def save_wallet_file(data):
    with open(WALLET_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ================= GENERATE =================
def generate_wallet(user_id):
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


# ================= IMPORT =================
def import_private_key(user_id, private_key):
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
    except:
        return None


def import_phrase(user_id, phrase):
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
    except:
        return None


# ================= LOAD =================
def load_wallet(user_id):
    data = load_wallet_file()
    user = data.get(str(user_id))

    if not user:
        return None

    decoded = base58.b58decode(user["private_key"])
    return Keypair.from_bytes(decoded)


def get_wallet_data(user_id):
    data = load_wallet_file()
    return data.get(str(user_id))


# ================= BALANCE =================
def get_balance(user_id):
    wallet = load_wallet(user_id)
    if not wallet:
        return 0

    balance = client.get_balance(wallet.pubkey())
    return balance['result']['value'] / 1e9


# ================= SIGN =================
def sign_and_send(user_id, tx_base64):
    wallet = load_wallet(user_id)

    tx_bytes = base64.b64decode(tx_base64)
    tx = VersionedTransaction.from_bytes(tx_bytes)

    tx.sign([wallet])

    return client.send_transaction(tx)