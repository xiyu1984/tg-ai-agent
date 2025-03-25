from dotenv import load_dotenv
import os

from flask import Flask, request, redirect, session
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
import json
import uuid
import threading  # Add this import at the top

# Load .env file
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv("API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:5000/oauth/callback"

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# User sessions to track authentication state
user_sessions = {}


application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# Replace dispatcher = updater.dispatcher with:
dispatcher = application

# Command handler for /start
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Generate a unique state token for this user
    state = str(uuid.uuid4())
    user_sessions[state] = {"telegram_id": user_id}
    
    # Create login URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
        f"&scope=email profile"
        f"&access_type=offline"
    )
    
    # Create inline keyboard with login button
    keyboard = [[InlineKeyboardButton("Login with Google", url=auth_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome! Please login with your Google account:",
        reply_markup=reply_markup
    )


async def goweb(update, context):
    user_id = update.effective_user.id
    
    # Generate a unique state token for this user
    state = str(uuid.uuid4())
    user_sessions[state] = {"telegram_id": user_id}
    url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
        f"&scope=email profile"
        f"&access_type=offline"
    )
    data = {
        "inline_keyboard": [[{"text": "🔗 Connect Google Account", "web_app": {"url": url}}]]
    }

    await update.message.reply_html(
        rf"Click the button to connect your google!",
        reply_markup=data
    )


# Flask route to handle OAuth callback
@app.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    # Get the authorization code and state
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state to prevent CSRF
    if state not in user_sessions:
        return "Invalid state parameter", 400
    
    telegram_id = user_sessions[state]["telegram_id"]
    
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    
    if "access_token" not in token_json:
        return "Failed to get access token", 400
    
    # Get user info with the access token
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    headers = {"Authorization": f"Bearer {token_json['access_token']}"}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info = user_info_response.json()
    
    # Store user info in session
    user_sessions[state]["google_user"] = user_info
    
    # Send message to user via Telegram
    send_message_to_telegram(telegram_id, f"Successfully logged in as {user_info.get('name', 'User')} ({user_info.get('email', 'No email')})")
    
    # Clean up session
    del user_sessions[state]
    
    return "Authentication successful! You can close this window and return to Telegram."


# ✅ Send Telegram Message After Binding
def send_message_to_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


# Start the bot and Flask server
# Update the start section:
if __name__ == '__main__':
    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("goweb", goweb))
    
    # Start Flask server in the main thread
    bot_thread = threading.Thread(target=app.run, args=('0.0.0.0', 5000), kwargs={'debug': False})
    bot_thread.daemon = True  # This makes the thread exit when the main program exits
    bot_thread.start()
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)
