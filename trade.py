import requests

# ================== CONFIG ==================
SOL = "So11111111111111111111111111111111111111112"

BASE_URL = "https://api.jup.ag/swap/v1"
QUOTE_URL = f"{BASE_URL}/quote"
SWAP_URL = f"{BASE_URL}/swap"

# ================== FUNCTIONS ==================

def get_token_price(token_mint: str) -> float | None:
    """
    Get the price of a token in terms of SOL.
    Returns price as float or None if failed.
    """
    try:
        params = {
            "inputMint": SOL,
            "outputMint": token_mint,
            "amount": 1_000_000_000,
            "slippageBps": 50
        }
        res = requests.get(QUOTE_URL, params=params, timeout=10)
        data = res.json()

        if not data.get("data"):
            print(f"[PRICE ERROR] No data for token {token_mint}")
            return None

        price = int(data["data"][0]["outAmount"]) / 1e6
        return price

    except Exception as e:
        print(f"[PRICE EXCEPTION] Token {token_mint}: {e}")
        return None


def get_quote(input_mint: str, output_mint: str, amount: int) -> dict | None:
    """
    Fetch a swap quote between two tokens.
    Returns quote dict or None if failed.
    """
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": 150,
        "onlyDirectRoutes": False
    }

    try:
        response = requests.get(QUOTE_URL, params=params, timeout=10)
        data = response.json()

        # Retry with higher slippage if no routes found
        if not data.get("data"):
            print("[QUOTE WARNING] No routes found, retrying with higher slippage...")
            params["slippageBps"] = 300
            response = requests.get(QUOTE_URL, params=params, timeout=10)
            data = response.json()
            if not data.get("data"):
                print("[QUOTE ERROR] Still no routes found.")
                return None

        return data

    except Exception as e:
        print(f"[QUOTE EXCEPTION] {e}")
        return None


def create_swap_tx(user_public_key: str, quote_response: dict) -> dict | None:
    """
    Create a swap transaction for the user.
    Returns swap response dict or None if failed.
    """
    payload = {
        "userPublicKey": user_public_key,
        "quoteResponse": quote_response,
        "wrapAndUnwrapSol": True
    }

    try:
        response = requests.post(SWAP_URL, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"[SWAP ERROR] {response.status_code}: {response.text}")
            return None

        return response.json()

    except Exception as e:
        print(f"[SWAP EXCEPTION] {e}")
        return None
