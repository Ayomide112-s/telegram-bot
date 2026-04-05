from flask import Flask, request

app = Flask(__name__)

@app.route("/save-wallet", methods=["POST"])
def save_wallet():
    data = request.json
    address = data.get("address")

    print("✅ Connected Wallet:", address)

    # You can store this in DB later

    return {"status": "success"}


if __name__ == "__main__":
    app.run(port=5000)