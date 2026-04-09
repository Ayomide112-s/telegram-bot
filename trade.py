import requests
import time

# ================= CONSTANT =================
SOL = "So11111111111111111111111111111111111111112"

JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

HEADERS = {
    "Content-Type": "application/json"
}

# ================= PRICE =================
def get_token_price(token_address):
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            return None

        data = res.json()

        pairs = data.get("pairs", [])
        if not pairs:
            return None

        # Pick best liquidity pair
        best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0)))

        price = best_pair.get("priceUsd")

        return float(price) if price else None

    except Exception as e:
        print("PRICE ERROR:", e)
        return None


# ================= TOKEN INFO =================
def get_token_info(token_address):
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            return None

        data = res.json()
        pairs = data.get("pairs", [])

        if not pairs:
            return None

        best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0)))

        return {
            "name": best_pair.get("baseToken", {}).get("name"),
            "symbol": best_pair.get("baseToken", {}).get("symbol"),
            "price": best_pair.get("priceUsd"),
            "liquidity": best_pair.get("liquidity", {}).get("usd"),
            "fdv": best_pair.get("fdv"),
            "volume24h": best_pair.get("volume", {}).get("h24"),
            "chart": best_pair.get("url")
        }

    except Exception as e:
        print("TOKEN INFO ERROR:", e)
        return None


# ================= QUOTE =================
def get_quote(input_mint, output_mint, amount):
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": 100,  # 1%
            "onlyDirectRoutes": False
        }

        res = requests.get(JUPITER_QUOTE_API, params=params, timeout=10)

        if res.status_code != 200:
            print("QUOTE ERROR:", res.text)
            return None

        data = res.json()

        routes = data.get("data")
        if not routes:
            return None

        return routes[0]  # best route

    except Exception as e:
        print("QUOTE ERROR:", e)
        return None


# ================= SWAP =================
def create_swap_tx(user_pubkey, quote):
    try:
        payload = {
            "userPublicKey": str(user_pubkey),
            "wrapAndUnwrapSol": True,
            "quoteResponse": quote
        }

        res = requests.post(JUPITER_SWAP_API, json=payload, headers=HEADERS, timeout=15)

        if res.status_code != 200:
            print("SWAP ERROR:", res.text)
            return None

        return res.json()

    except Exception as e:
        print("SWAP ERROR:", e)
        return None
