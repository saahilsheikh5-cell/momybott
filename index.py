import os
import telebot
from flask import Flask, request

# === Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://momybott-4.onrender.com/" + BOT_TOKEN)
CHAT_ID = int(os.getenv("CHAT_ID", "1263295916"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# === Telegram Bot Handlers ===
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🤖 Bot is alive and running on Render!")

# === Flask Routes ===
@app.route("/", methods=["GET"])
def home():
    return "✅ Bot server is running!", 200

@app.route("/" + BOT_TOKEN, methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# === Startup Hook ===
@app.before_first_request
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

