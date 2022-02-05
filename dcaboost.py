import threading
import traceback
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dcaboostutils import json, time, query, query_main, create_pair, get_settings, get_account_summary_text, amount_format

TRADING_ENGINE_ACTIVE = 0
LOCK_QUERY_ACTIVE = 0
API_LABEL_KEY = "APILabel"

MASTER_ACCOUNT = "MASTER"
SUB_ACCOUNT = "SUBACCOUNT"

DCA_SETTINGS_KEY = "DCA"

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
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " " + function.__name__ + " command requested by " + update.effective_user.username)

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

def get_sub_accounts():
    json_result = None
    method = "private/subaccount/get-sub-accounts"
    params = {
        }
    query_result = query_main(method, params)
    if query_result:
        json_result = json.loads(query_result.text)
    return json_result

def get_account_summary(currency = None):
    method = "private/get-account-summary"
    params = {}
    if currency:
        params["currency"] = currency
    result = query(method, params)
    return json.loads(result.text)

def get_available_quantity(currency):
    summary = get_account_summary(currency)
    available = 0
    if summary and summary["result"] and summary["result"]["accounts"]:
        available = summary["result"]["accounts"][0]["available"]
    return available

def get_current_subaccount():
    settings = get_settings()
    account_label = settings[API_LABEL_KEY]
    result = None
    sub_accounts = get_sub_accounts()
    if sub_accounts and sub_accounts["result"]:
        for sub_account in sub_accounts["result"]["sub_account_list"]:
            if sub_account["label"] == account_label:
                result = sub_account
                break
    return result

def get_sub_account_uuid():
    sub_account_uuid = None
    sub_account = get_current_subaccount()
    if sub_account:
        sub_account_uuid = sub_account["uuid"]
    return sub_account_uuid

def transfer_amount(from_account, to_account, amount, currency):
    json_result = None
    method = "private/subaccount/transfer"
    params = {
        "from": from_account,
        "to": to_account,
        "sub_account_uuid": get_sub_account_uuid(),
        "currency": currency,
        "amount": amount
        }
    query_result = query_main(method, params)
    if query_result:
        json_result = json.loads(query_result.text)
    return json_result

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

def get_trades(crypto, base, start_time, end_time = None):
    method = "private/get-trades"
    params = {
        "instrument_name": create_pair(crypto, base),
        "start_ts": start_time
    }
    #If end_time is not provided, let's set it as current time
    if not end_time:
        end_time = int(time.time())*1000
        params["end_ts"] = end_time
        exit_query = 0
        while not exit_query:
            global LOCK_QUERY_ACTIVE
            if not LOCK_QUERY_ACTIVE:
                LOCK_QUERY_ACTIVE = 1
                time.sleep(1)
                result = query(method, params)
                LOCK_QUERY_ACTIVE = 0
                exit_query = 1
            else:
                time.sleep(1)
    trades = None
    if result:
        json_result = json.loads(result.text)
        if json_result and json_result["result"]:
            trades = json_result["result"]["trade_list"]
    return trades

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
        settings = get_settings()
        dca_settings = settings[DCA_SETTINGS_KEY]
        if dca_settings:
            for dca in dca_settings:
                crypto = dca[CRYPTO_CURRENCY_KEY]
                base = dca[BASE_CURRENCY_KEY]
                buy_amount = dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]
                frequency = dca[FREQUENCY_IN_HOUR_KEY] * SECONDS_IN_ONE_HOUR
                print(time.strftime("%Y-%m-%d %H:%M:%S") + " Starting DCA on " + crypto + ", buying " + str(buy_amount) + " " + base + " every " + str(frequency) + " seconds")
                dca_thread = threading.Thread(target = execute_dca, args = (settings, crypto, base, buy_amount, frequency), daemon = True)
                time.sleep(1)
                dca_thread.start()
    except Exception:
        stop_trading_engine()
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Error in the execution of the engine: " + str(traceback.print_exc()))
        start_trading_engine()
    return

def execute_dca(settings, crypto, base, buy_amount, frequency):
    global TRADING_ENGINE_ACTIVE
    while TRADING_ENGINE_ACTIVE:
        wait_from_last_trade(crypto, base, frequency)
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Transfering " + str(buy_amount) + " " + base + " from " + MASTER_ACCOUNT)
        transfer_amount(MASTER_ACCOUNT,SUB_ACCOUNT, buy_amount, base)
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Buying " + str(buy_amount) + " " + base + " of " + crypto)
        order = create_buy_order(crypto, base, buy_amount)
        order_id = get_order_id(order)
        if order_id:
            order_detail = get_order_detail(order_id)
            print(order_detail)
        available_quantity = get_available_quantity(crypto)
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Transfering " + amount_format(available_quantity) + " " + crypto + " from " + settings[API_LABEL_KEY])
        transfer_amount(SUB_ACCOUNT,MASTER_ACCOUNT, available_quantity, crypto)

def wait_from_last_trade(crypto, base, frequency):
    expected_last_trade = (int(time.time()) - frequency) * 1000
    time_until_next_trade = frequency
    trades = get_trades(crypto, base, expected_last_trade)
    if trades:
        most_recent_trade = 0
        for trade in trades:
            if most_recent_trade < trade["create_time"]:
                most_recent_trade = trade["create_time"]
        time_until_next_trade = int((most_recent_trade + frequency*1000 - int(time.time()*1000))/1000)
    elif trades is not None:
        time_until_next_trade = 1
    print(time.strftime("%Y-%m-%d %H:%M:%S") + " Waiting " + str(time_until_next_trade) + " seconds before next buy order of " + crypto + " is placed")
    time.sleep(time_until_next_trade)

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