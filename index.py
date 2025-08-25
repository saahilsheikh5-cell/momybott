import os
import telebot
import requests
import time
import threading
import numpy as np
import pandas as pd
from flask import Flask, request
from telebot import types

# === CONFIG ===
BOT_TOKEN = "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q"
WEBHOOK_URL = "https://momybott-4.onrender.com/" + BOT_TOKEN
CHAT_ID = 1263295916

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# === Startup logic replacement for Flask 3.1+ ===
def run_startup_task():
    # Put any startup logic you had in before_first_request
    print(">>> Startup task running...")

@app.before_request
def activate_job():
    if not hasattr(app, 'job_started'):
        app.job_started = True
        threading.Thread(target=run_startup_task).start()

# === Routes ===
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def index():
    return "Bot is running!", 200

# === Example Bot Handler ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hello! I am alive and working on Render!")

# === Start webhook ===
def start_bot():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    start_bot()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


