from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dcaboostutils import get_settings, get_account_summary_text
from dcaboost import get_trading_engine_status_text, start_trading_engine, stop_trading_engine

BOT_TOKEN_KEY = 'TelegramBotToken'
BOT_USERS_KEY = "Users"

def isAuthorized(update):
    return update.effective_user.username in get_users()

def get_users():
    credentials = get_settings()
    users = credentials[BOT_USERS_KEY]
    return users

def genericHandler(update, context, function):
    if(isAuthorized(update)):
        output = function()
        context.bot.send_message(chat_id=update.effective_chat.id, text=output)
    else:
        print(function.__name__ + " command requested by " + update.effective_user.username)

def get_start_message():
    return "Welcome to crobot! Use /help to retrieve the command list"

def get_help_message():
    return "Here's the command list:\n" \
        "/wallet to display your wallets\n" \
        "/status to check the trading engine status\n" \
        "/startengine to start the trading engine\n" \
        "/stopengine to stop the trading engine\n"

def get_unknown_message():
    return "Sorry, I didn't understand that command."

def start(update, context):
    genericHandler(update,context, get_start_message)

def displayHelp(update, context):
    genericHandler(update, context, get_help_message)

def displayWallet(update, context):
    genericHandler(update, context, get_account_summary_text)

def startEngine(update, context):
    genericHandler(update, context, start_trading_engine)

def stopEngine(update, context):
    genericHandler(update, context, stop_trading_engine)

def status(update, context):
    genericHandler(update, context, get_trading_engine_status_text)

def unknown(update, context):
    genericHandler(update, context, get_unknown_message)


credentials = get_settings()
tokenData = credentials[BOT_TOKEN_KEY]
updater = Updater(token=tokenData)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
displayCommand_handler = CommandHandler('help', displayHelp)
displayWallet_handler = CommandHandler('wallet', displayWallet)
startEngine_handler = CommandHandler('startengine', startEngine)
stopEngine_handler = CommandHandler('stopengine', stopEngine)
status_handler = CommandHandler('status', status)
unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(displayCommand_handler)
dispatcher.add_handler(displayWallet_handler)
dispatcher.add_handler(startEngine_handler)
dispatcher.add_handler(stopEngine_handler)
dispatcher.add_handler(status_handler)
dispatcher.add_handler(unknown_handler)
updater.start_polling()
print("Bot is active and running")
updater.idle()
