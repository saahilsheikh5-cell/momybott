import os
import telebot
import requests
import pandas as pd
import threading
import time
import json
import numpy as np
from telebot import types
from flask import Flask, request

# ================= CONFIG =================
BOT_TOKEN = "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q"
WEBHOOK_URL = "https://momybott-4.onrender.com/" + BOT_TOKEN
CHAT_ID = 1263295916

KLINES_URL = "https://api.binance.com/api/v3/klines"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= STORAGE =================
USER_COINS_FILE = "user_coins.json"
SETTINGS_FILE = "settings.json"
SENT_SIGNALS_FILE = "sent_signals.json"

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

coins = load_json(USER_COINS_FILE, [])
settings = load_json(SETTINGS_FILE, {"RSI_BUY": 15, "RSI_SELL": 85})
sent_signals = load_json(SENT_SIGNALS_FILE, {})

def save_coins(): save_json(USER_COINS_FILE, coins)
def save_settings(): save_json(SETTINGS_FILE, settings)
def save_sent(): save_json(SENT_SIGNALS_FILE, sent_signals)

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

def generate_signal(symbol, timeframe="15m"):
    try:
        closes = get_klines(symbol, timeframe, 100)
        if len(closes) < 20: return None
        last_close = closes[-1]
        rsi_val = rsi(closes)[-1]

        if rsi_val < settings["RSI_BUY"]:
            return f"🟢 STRONG BUY {symbol} ({timeframe}) | RSI {rsi_val:.2f} | Price {last_close}"
        elif rsi_val > settings["RSI_SELL"]:
            return f"🔴 STRONG SELL {symbol} ({timeframe}) | RSI {rsi_val:.2f} | Price {last_close}"
        return None
    except:
        return None

# ================= BACKGROUND SIGNALS =================
auto_signals_enabled = True

def signal_scanner():
    while True:
        if auto_signals_enabled:
            for coin in coins:
                for tf in TIMEFRAMES:
                    sig = generate_signal(coin, tf)
                    last_sent = sent_signals.get(coin, {}).get(tf)
                    if sig:
                        if last_sent != sig:
                            bot.send_message(CHAT_ID, f"⚡ {sig}")
                            if coin not in sent_signals: sent_signals[coin] = {}
                            sent_signals[coin][tf] = sig
                    else:
                        # Clear last signal if it’s no longer valid
                        if coin in sent_signals and tf in sent_signals[coin]:
                            del sent_signals[coin][tf]
            save_sent()
        time.sleep(60)

threading.Thread(target=signal_scanner, daemon=True).start()

# ================= HANDLERS =================
@bot.message_handler(commands=["start"])
def start(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 My Coins", "➕ Add Coin")
    markup.add("➖ Remove Coin", "🤖 Auto Signals")
    markup.add("🛑 Stop Signals", "✅ Resume Signals")
    markup.add("⚙️ Settings", "🔄 Reset Settings", "📡 Signals")
    bot.send_message(msg.chat.id, "🤖 Welcome! Choose an option:", reply_markup=markup)

# --- My Coins ---
@bot.message_handler(func=lambda m: m.text == "📊 My Coins")
def my_coins(msg):
    if not coins:
        bot.send_message(msg.chat.id, "⚠️ No coins saved. Use ➕ Add Coin.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for coin in coins: markup.add(coin)
    bot.send_message(msg.chat.id, "📊 Select a coin:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Add Coin")
def add_coin(msg):
    bot.send_message(msg.chat.id, "Type coin symbol (e.g., BTCUSDT):")
    bot.register_next_step_handler(msg, process_add_coin)

def process_add_coin(msg):
    coin = msg.text.upper()
    if coin not in coins:
        coins.append(coin)
        save_coins()
        bot.send_message(msg.chat.id, f"✅ {coin} added.")
    else:
        bot.send_message(msg.chat.id, f"{coin} already exists.")

@bot.message_handler(func=lambda m: m.text == "➖ Remove Coin")
def remove_coin(msg):
    if not coins:
        bot.send_message(msg.chat.id, "⚠️ No coins to remove.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for coin in coins: markup.add(coin)
    bot.send_message(msg.chat.id, "Select coin to remove:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_remove_coin)

def process_remove_coin(msg):
    coin = msg.text.upper()
    if coin in coins:
        coins.remove(coin)
        save_coins()
        bot.send_message(msg.chat.id, f"❌ {coin} removed.")
    else: bot.send_message(msg.chat.id, "Coin not found.")

# --- Auto Signals ---
@bot.message_handler(func=lambda m: m.text == "🤖 Auto Signals")
def enable_signals(msg):
    global auto_signals_enabled
    auto_signals_enabled = True
    bot.send_message(msg.chat.id, "✅ Auto signals ENABLED.")

@bot.message_handler(func=lambda m: m.text == "🛑 Stop Signals")
def stop_signals(msg):
    global auto_signals_enabled
    auto_signals_enabled = False
    bot.send_message(msg.chat.id, "⛔ Auto signals DISABLED.")

@bot.message_handler(func=lambda m: m.text == "✅ Resume Signals")
def resume_signals(msg):
    global auto_signals_enabled
    auto_signals_enabled = True
    bot.send_message(msg.chat.id, "✅ Auto signals RESUMED.")

# --- Settings ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def settings_menu(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(f"🔺 RSI Buy ({settings['RSI_BUY']})", f"🔻 RSI Sell ({settings['RSI_SELL']})")
    markup.add("⬅️ Back")
    bot.send_message(msg.chat.id, "⚙️ Adjust Settings:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith("🔺 RSI Buy"))
def adjust_rsi_buy(msg):
    bot.send_message(msg.chat.id, "Type new RSI Buy threshold (5-50):")
    bot.register_next_step_handler(msg, set_rsi_buy)

def set_rsi_buy(msg):
    try:
        val = int(msg.text)
        if 5 <= val <= 50:
            settings["RSI_BUY"] = val
            save_settings()
            bot.send_message(msg.chat.id, f"✅ RSI Buy set to {val}")
        else:
            bot.send_message(msg.chat.id, "⚠️ Value out of range.")
    except:
        bot.send_message(msg.chat.id, "⚠️ Invalid input.")

@bot.message_handler(func=lambda m: m.text.startswith("🔻 RSI Sell"))
def adjust_rsi_sell(msg):
    bot.send_message(msg.chat.id, "Type new RSI Sell threshold (50-95):")
    bot.register_next_step_handler(msg, set_rsi_sell)

def set_rsi_sell(msg):
    try:
        val = int(msg.text)
        if 50 <= val <= 95:
            settings["RSI_SELL"] = val
            save_settings()
            bot.send_message(msg.chat.id, f"✅ RSI Sell set to {val}")
        else:
            bot.send_message(msg.chat.id, "⚠️ Value out of range.")
    except:
        bot.send_message(msg.chat.id, "⚠️ Invalid input.")

# --- Reset ---
@bot.message_handler(func=lambda m: m.text == "🔄 Reset Settings")
def reset_settings(msg):
    global coins, settings, sent_signals
    coins = []
    settings = {"RSI_BUY": 15, "RSI_SELL": 85}
    sent_signals = {}
    save_coins(); save_settings(); save_sent()
    bot.send_message(msg.chat.id, "🔄 Settings reset. All coins cleared.")

# --- Signals Command ---
@bot.message_handler(commands=["signals"])
@bot.message_handler(func=lambda m: m.text == "📡 Signals")
def signals(msg):
    if not coins:
        bot.send_message(msg.chat.id, "⚡ No coins saved.")
        return
    strong_signals = []
    for coin in coins:
        for tf in TIMEFRAMES:
            sig = generate_signal(coin, tf)
            last_sent = sent_signals.get(coin, {}).get(tf)
            if sig and last_sent != sig:
                strong_signals.append(sig)
                if coin not in sent_signals: sent_signals[coin] = {}
                sent_signals[coin][tf] = sig
    save_sent()
    if not strong_signals:
        bot.send_message(msg.chat.id, "⚡ No strong signals right now.")
    else:
        bot.send_message(msg.chat.id, "📡 Ultra-Filtered Signals:\n\n" + "\n".join(strong_signals))

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




