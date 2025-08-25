import os
import telebot
import requests
from flask import Flask, request
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN", "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://momybott-4.onrender.com/" + BOT_TOKEN)
CHAT_ID = int(os.getenv("CHAT_ID", "1263295916"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/" + BOT_TOKEN, methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

def run_bot():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

# Start webhook thread immediately when app loads
threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
