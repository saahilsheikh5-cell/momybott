import os
import telebot
import requests
import pandas as pd
import threading
import time
import json
from telebot import types
from flask import Flask, request
import numpy as np

# ================= CONFIG =================
BOT_TOKEN = "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q"
WEBHOOK_URL = "https://momybott-4.onrender.com/" + BOT_TOKEN
CHAT_ID = 1263295916

# Binance API endpoints
KLINES_URL = "https://api.binance.com/api/v3/klines"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= STORAGE =================
USER_COINS_FILE = "user_coins.json"

def load_data():
    if not os.path.exists(USER_COINS_FILE):
        return {"coins": [], "settings": {"rsi_buy": 25, "rsi_sell": 75, "coin_intervals": {}}}
    with open(USER_COINS_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(USER_COINS_FILE, "w") as f:
        json.dump(data, f, indent=4)

data_store = load_data()

def load_coins():
    return data_store.get("coins", [])

def save_coins(coins):
    data_store["coins"] = coins
    save_data(data_store)

settings = data_store.get("settings", {"rsi_buy": 25, "rsi_sell": 75, "coin_intervals": {}})

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
        interval = settings['coin_intervals'].get(symbol, "15m")
        closes = get_klines(symbol, interval, 100)
        if len(closes) < 20:
            return None
        last_close = closes[-1]
        rsi_val = rsi(closes)[-1]

        if rsi_val < settings['rsi_buy']:
            return f"🟢 STRONG BUY {symbol} | RSI {rsi_val:.2f} | Price {last_close}"
        elif rsi_val > settings['rsi_sell']:
            return f"🔴 STRONG SELL {symbol} | RSI {rsi_val:.2f} | Price {last_close}"
        return None
    except Exception:
        return None

# ================= BACKGROUND SIGNALS =================
auto_signals_enabled = True
active_signals = {}  # { "BTCUSDT": expiry_timestamp }

def signal_scanner():
    while True:
        if auto_signals_enabled:
            coins = load_coins() or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
            now = time.time()
            for c in coins:
                interval = settings['coin_intervals'].get(c, "15m")
                sig = generate_signal(c)
                if sig and (c not in active_signals or active_signals[c] < now):
                    # Set validity based on interval
                    validity_seconds = {
                        "1m": 60,
                        "5m": 5*60,
                        "15m": 15*60,
                        "1h": 60*60,
                        "4h": 4*60*60,
                        "1d": 24*60*60
                    }.get(interval, 15*60)  # default 15m
                    active_signals[c] = now + validity_seconds
                    bot.send_message(CHAT_ID, f"⚡ {sig} | Valid for {validity_seconds//60} min")
        time.sleep(30)

threading.Thread(target=signal_scanner, daemon=True).start()

# ================= HANDLERS =================
@bot.message_handler(commands=["start"])
def start(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 My Coins", "➕ Add Coin")
    markup.add("➖ Remove Coin", "🤖 Auto Signals")
    markup.add("🛑 Stop Signals", "🔄 Reset Settings")
    markup.add("📡 Signals", "⚙️ Settings")
    bot.send_message(msg.chat.id, "🤖 Welcome! Choose an option:", reply_markup=markup)

# --- My Coins ---
@bot.message_handler(func=lambda m: m.text == "📊 My Coins")
def my_coins(msg):
    coins = load_coins()
    if not coins:
        bot.send_message(msg.chat.id, "⚠️ No coins saved. Use ➕ Add Coin.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for coin in coins:
        markup.add(coin)
    bot.send_message(msg.chat.id, "📊 Select a coin:", reply_markup=markup)

# --- Add Coin ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Coin")
def add_coin(msg):
    bot.send_message(msg.chat.id, "Type coin symbol (e.g., BTCUSDT):")
    bot.register_next_step_handler(msg, process_add_coin)

def process_add_coin(msg):
    coin = msg.text.upper()
    coins = load_coins()
    if coin not in coins:
        coins.append(coin)
        save_coins(coins)
        bot.send_message(msg.chat.id, f"✅ {coin} added.")
    else:
        bot.send_message(msg.chat.id, f"{coin} already exists.")

# --- Remove Coin ---
@bot.message_handler(func=lambda m: m.text == "➖ Remove Coin")
def remove_coin(msg):
    coins = load_coins()
    if not coins:
        bot.send_message(msg.chat.id, "⚠️ No coins to remove.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for coin in coins:
        markup.add(coin)
    bot.send_message(msg.chat.id, "Select coin to remove:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_remove_coin)

def process_remove_coin(msg):
    coin = msg.text.upper()
    coins = load_coins()
    if coin in coins:
        coins.remove(coin)
        save_coins(coins)
        bot.send_message(msg.chat.id, f"❌ {coin} removed.")
    else:
        bot.send_message(msg.chat.id, "Coin not found.")

# --- Auto Signals Toggle ---
@bot.message_handler(func=lambda m: m.text == "🤖 Auto Signals")
def enable_signals(msg):
    global auto_signals_enabled
    auto_signals_enabled = True
    bot.send_message(msg.chat.id, "✅ Auto signals ENABLED.")

@bot.message_handler(func=lambda m: m.text == "🛑 Stop Signals")
def stop_signals(msg):
    global auto_signals_enabled, active_signals
    auto_signals_enabled = False
    active_signals.clear()
    bot.send_message(msg.chat.id, "⛔ Auto signals and active signals STOPPED.")

# --- Reset ---
@bot.message_handler(func=lambda m: m.text == "🔄 Reset Settings")
def reset_settings(msg):
    save_coins([])
    data_store["settings"] = {"rsi_buy": 25, "rsi_sell": 75, "coin_intervals": {}}
    save_data(data_store)
    bot.send_message(msg.chat.id, "🔄 Settings reset. All coins cleared.")

# --- Signals Command ---
@bot.message_handler(commands=["signals"])
@bot.message_handler(func=lambda m: m.text == "📡 Signals")
def signals(msg):
    coins = load_coins() or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    strong_signals = []
    for c in coins:
        sig = generate_signal(c)
        if sig:
            strong_signals.append(sig)
    if not strong_signals:
        bot.send_message(msg.chat.id, "⚡ No strong signals right now.")
    else:
        bot.send_message(msg.chat.id, "📡 Ultra-Filtered Signals:\n\n" + "\n".join(strong_signals))

# --- Settings Command ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def settings_handler(msg):
    bot.send_message(msg.chat.id, "Current RSI thresholds:\n"
                     f"Buy: {settings['rsi_buy']}\n"
                     f"Sell: {settings['rsi_sell']}\n"
                     "You can change them by typing:\n"
                     "Buy=VALUE Sell=VALUE")
    bot.register_next_step_handler(msg, process_settings)

def process_settings(msg):
    try:
        text = msg.text.replace(" ", "")
        parts = text.split("Sell=")
        buy_val = int(parts[0].split("Buy=")[1])
        sell_val = int(parts[1])
        settings['rsi_buy'] = buy_val
        settings['rsi_sell'] = sell_val
        save_data(data_store)
        bot.send_message(msg.chat.id, f"✅ Settings updated: Buy={buy_val}, Sell={sell_val}")
    except Exception:
        bot.send_message(msg.chat.id, "⚠️ Invalid format. Use: Buy=VALUE Sell=VALUE")

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

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


