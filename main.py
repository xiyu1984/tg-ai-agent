from dotenv import load_dotenv
import os

import logging
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

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

def main() -> None:
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
    application.add_handler(CommandHandler("twitter", twitter))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()