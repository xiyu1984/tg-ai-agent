from dotenv import load_dotenv
import os

import logging
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import ollama
import torch

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def goweb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = {
        "inline_keyboard": [[{"text": "Open WebApp", "web_app": {"url": 'https://www.google.com'}}]]
    }

    await update.message.reply_html(
        rf"Click the button to open WebApp!",
        reply_markup=data
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def twitter(update, context):
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    user_name = update.effective_user.name

    print('telegram user: ', user_id, ':', user_name, '. in chat: ', chat_id)

    button = InlineKeyboardButton(
        text="🔗 Connect Twitter Account",
        url=os.getenv('TWITTER_AUTH_URL') + f"?chat_id={chat_id}"
    )
    keyboard = InlineKeyboardMarkup([[button]])
    await context.bot.send_message(
        chat_id=chat_id,
        text="Click the button below to connect your Twitter account:",
        reply_markup=keyboard
    )

async def twweb(update, context):
    TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
    TWITTER_CALLBACK_URL = os.getenv('TWITTER_CALLBACK_URL')

    chat_id = update.message.chat_id
    url = f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={TWITTER_CLIENT_ID}&redirect_uri={TWITTER_CALLBACK_URL}&scope=tweet.read%20users.read%20offline.access&state={chat_id}&code_challenge=challenge&code_challenge_method=plain"
    data = {
        "inline_keyboard": [[{"text": "🔗 Connect Twitter Account", "web_app": {"url": url}}]]
    }

    await update.message.reply_html(
        rf"Click the button to connect your twitter!",
        reply_markup=data
    )

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Chat with AI."""
    response = ollama.chat(
        model='deepseek-r1:8b',
        messages=[{
            'role': 'user',
            'content': update.message.text,
        }]
    )
    print(response.message.content)

    left_len = len(response.message.content)
    cur_idx = 0
    while left_len > 0:
        out_len = min(2000, left_len)
        await update.message.reply_text(response.message.content[cur_idx:(cur_idx + out_len)])
        cur_idx += out_len
        left_len -= out_len


def main() -> None:
    # init ollma
    print(torch.backends.mps.is_available())  # Should return True if MPS is supported
    print(torch.backends.mps.is_built())  # Check if MPS is built into your PyTorch version

    # Load .env file
    load_dotenv()

    # Your Bot Token
    TOKEN = os.getenv("API_KEY")

    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("goweb", goweb))
    application.add_handler(CommandHandler("twitter", twitter))
    application.add_handler(CommandHandler("twweb", twweb))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()