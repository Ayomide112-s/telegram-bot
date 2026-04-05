import requests

QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
SWAP_URL = "https://quote-api.jup.ag/v6/swap"

SOL = "So11111111111111111111111111111111111111112"

def get_market_price(symbol):
    try:
        token_id = TOKEN_MAP.get(symbol.upper())

        if not token_id:
            return None

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": token_id,
            "vs_currencies": "usd"
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        if token_id in data:
            return data[token_id]["usd"]

        return None

    except Exception as e:
        print("Market Price Error:", e)
        return None


def get_quote(token_mint, amount_lamports):
    try:
        params = {
            "inputMint": SOL,
            "outputMint": token_mint,
            "amount": amount_lamports,
            "slippageBps": 50
        }

        res = requests.get(QUOTE_URL, params=params, timeout=10)
        data = res.json()

        if "data" not in data or not data["data"]:
            return None

        return data["data"][0]

    except:
        return None

TOKEN_MAP = {
    "BONK": "bonk",
    "SOL": "solana",
    "ETH": "ethereum",
    "BTC": "bitcoin"
}
def create_swap_tx(quote, user_pubkey):
    try:
        body = {
            "quoteResponse": quote,
            "userPublicKey": str(user_pubkey),
            "wrapUnwrapSOL": True
        }

        res = requests.post(SWAP_URL, json=body, timeout=15)
        return res.json()

    except:
        return None