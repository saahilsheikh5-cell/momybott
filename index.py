import os
import telebot
import requests
import pandas as pd
import threading
import time
from telebot import types
from flask import Flask, request
import numpy as np

# ================= CONFIG =================
BOT_TOKEN = "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q"
WEBHOOK_URL = "https://momybott-4.onrender.com/" + BOT_TOKEN
CHAT_ID = 1263295916

# Binance API endpoints
ALL_COINS_URL = "https://api.binance.com/api/v3/ticker/24hr"
KLINES_URL = "https://api.binance.com/api/v3/klines"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= STORAGE =================
USER_COINS_FILE = "user_coins.txt"

def load_coins():
    if not os.path.exists(USER_COINS_FILE):
        return []
    with open(USER_COINS_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def save_coins(coins):
    with open(USER_COINS_FILE, "w") as f:
        for c in coins:
            f.write(c + "\n")

# ================= TECHNICAL ANALYSIS =================
def get_klines(symbol, interval="15m", limit=100):
    url = f"{KLINES_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url, timeout=10).json()
    closes = [float(c[4]) for c in data]
    return closes

def rsi(data, period=14):
    delta = np.diff(data)
    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)
    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def generate_signal(symbol):
    try:
        closes = get_klines(symbol, "15m", 100)
        if len(closes) < 20:
            return None
        last_close = closes[-1]
        rsi_val = rsi(closes)[-1]

        if rsi_val < 25:
            return f"🟢 STRONG BUY {symbol} | RSI {rsi_val:.2f} | Price {last_close}"
        elif rsi_val > 75:
            return f"🔴 STRONG SELL {symbol} | RSI {rsi_val:.2f} | Price {last_close}"
        return None
    except Exception:
        return None

# ================= BACKGROUND SIGNALS =================
auto_signals_enabled = True

def signal_scanner():
    while True:
        if auto_signals_enabled:
            coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
            for c in coins:
                sig = generate_signal(c)
                if sig:
                    bot.send_message(CHAT_ID, f"⚡ {sig}")
        time.sleep(60)

# ================= HANDLERS =================
@bot.message_handler(commands=["start"])
def start(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 My Coins", "➕ Add Coin")
    markup.add("➖ Remove Coin", "🚀 Top Movers")
    markup.add("🤖 Auto Signals", "🛑 Stop Signals")
    markup.add("🔄 Reset Settings", "📡 Signals")
    bot.send_message(msg.chat.id, "🤖 Welcome! Choose an option:", reply_markup=markup)

# My Coins, Add, Remove etc... (same as before)

# ================= FLASK (WEBHOOK) =================
@app.route("/" + BOT_TOKEN, methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot running!", 200

# ================= MAIN =================
if __name__ == "__main__":
    # Remove previous webhook
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    # Start background thread
    threading.Thread(target=signal_scanner, daemon=True).start()

    # Run Flask server on Render-assigned port
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
