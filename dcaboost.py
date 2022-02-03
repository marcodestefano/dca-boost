import threading
import traceback
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dcaboostutils import json, time, query, create_pair, get_settings, get_account_summary_text

TRADING_ENGINE_ACTIVE = 0

CRYPTO_CURRENCY_KEY = "CRYPTO_CURRENCY"
BASE_CURRENCY_KEY = "BASE_CURRENCY"
BUY_AMOUNT_IN_BASE_CURRENCY_KEY = "BUY_AMOUNT_IN_BASE_CURRENCY"
FREQUENCY_IN_HOUR_KEY = "FREQUENCY_IN_HOUR"
SECONDS_IN_ONE_HOUR = 60*60

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
    return "Welcome to dcaboost! Use /help to retrieve the command list"

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

def create_buy_order(crypto, base, buy_amount):
    json_result = None
    method = "private/create-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "side": "BUY",
        "type": "MARKET",
        "notional": buy_amount
        }
    query_result = query(method, params)
    if query_result:
        json_result = json.loads(query_result.text)
    return json_result

def get_order_detail(order_id):
    json_result = None
    method = "private/get-order-detail"
    params = {
        "order_id": order_id
        }
    query_result = query(method, params)
    if query_result:
        json_result = json.loads(query_result.text)
    return json_result

def get_order_id(order):
    order_id = None
    if order and order["result"]:
        order_id = order["result"]["order_id"]
    return order_id

def start_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if not TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 1
        tradingEngineThread = threading.Thread(target = execute_trading_engine)
        tradingEngineThread.start()
        result = "Trading engine correctly started"
    else:
        result =  "Trading engine is already running"
    print(result)
    return result

def stop_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 0
        result = "Trading engine stopped"
    else:
        result = "Trading engine already stopped"
    print(result)
    return result

def get_trading_engine_status_text():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        result = "Trading engine is running"
    else:
        result = "Trading engine is not running"
    return result

def execute_trading_engine():
    try:
        global TRADING_ENGINE_ACTIVE
        while TRADING_ENGINE_ACTIVE:
            settings = get_settings()
            crypto = settings[CRYPTO_CURRENCY_KEY]
            base = settings[BASE_CURRENCY_KEY]
            buy_amount = settings[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]
            frequency = settings[FREQUENCY_IN_HOUR_KEY] * SECONDS_IN_ONE_HOUR
            print("Buying " + str(settings[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]) + " " + base + " of " + crypto)
            order = create_buy_order(crypto, base, buy_amount)
            order_id = get_order_id(order)
            if order_id:
                order_detail = get_order_detail(order_id)
                print(order_detail)
            print("Waiting " + str(settings[FREQUENCY_IN_HOUR_KEY]) + " hour(s) before next buy order is placed")
            time.sleep(frequency)
    except Exception:
        stop_trading_engine()
        print("Error in the execution of the engine: " + str(traceback.print_exc()))
        start_trading_engine()
    return

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