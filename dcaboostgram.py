import threading
from telegram import MAX_MESSAGE_LENGTH, Update
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackContext
from dcaboostutils import DATA_MAIN_API_KEY, DATA_MAIN_API_SECRET, DATA_SUB_API_KEY, DATA_SUB_API_SECRET, DATA_SUB_API_LABEL, DATA_DCA_CONFIG, time, save_account, get_telegram_settings, get_account, send_message, test_api, get_instrument, mask, amount_format
from dcaboost import CRYPTO_CURRENCY_KEY, BASE_CURRENCY_KEY, BUY_AMOUNT_IN_BASE_CURRENCY_KEY, FREQUENCY_IN_HOUR_KEY, SECONDS_IN_ONE_HOUR, transfer_to_master_account, transfer_to_sub_account, wait_time_from_last_trade, create_buy_order

BOT_TOKEN_KEY = 'TelegramBotToken'
ERROR_HANDLER_ID = "ErrorID"
NEGATIVE_BALANCE = "NEGATIVE_BALANCE"

HOURLY_FREQUENCE = "HOURLY"
DAILY_FREQUENCE = "DAILY"
WEEKLY_FREQUENCE = "WEEKLY"
BI_WEEKLY_FREQUENCE = "BI-WEEKLY"
FREQUENCIES = [HOURLY_FREQUENCE, DAILY_FREQUENCE, WEEKLY_FREQUENCE, BI_WEEKLY_FREQUENCE]

MAIN_API_KEY, MAIN_API_SECRET, SUB_API_KEY, SUB_API_SECRET, SUB_API_LABEL = range(5)

RUNNING_ENGINES = {}

def start(update: Update, context: CallbackContext) -> None:
    first_name = update.effective_chat.first_name
    if not first_name:
        first_name = ""
    bot = context.bot
    chat_id = update.effective_chat.id
    text = "Welcome to dcaboost, " + first_name + "! Use /setup to setup your account"
    if get_account(chat_id):
        text = "Welcome back to dcaboost, " + first_name + "! You already have an account, use /help to display the available commands"
    send_message(update, context, text)

def help(update: Update, context: CallbackContext) -> None:
    text = "Here's the command list:\n" \
        "/setup to setup your account\n" \
        "/mydca to display your DCA strategy\n" \
        "/adddca to add a new DCA strategy to your account\n" \
        "/removedca to remove one DCA strategy from your account\n" \
        "/status to check the trading engine status\n" \
        "/startengine to start the trading engine\n" \
        "/stopengine to stop the trading engine\n" \
        "/deleteaccount to delete your account"
    send_message(update, context, text)

def setup(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    text = ""
    conversation_next_step = ConversationHandler.END
    account = get_account(chat_id)
    if account:
        text = "You already have an account setup. Please /delete your account if you want to setup it again"
    else:
        text = """Great, let's start the setup of your account. To cancel the operation, just send /cancel anytime.\n 
        Please write your main account Api Key"""
        conversation_next_step = MAIN_API_KEY
    send_message(update, context, text)
    return conversation_next_step

def set_main_api_key(update: Update, context: CallbackContext) -> int:
    apikey = update.message.text
    context.user_data[DATA_MAIN_API_KEY] = apikey
    text = "Ok, now please write your main account API Secret"
    send_message(update, context, text)
    return MAIN_API_SECRET

def set_main_api_secret(update: Update, context: CallbackContext) -> int:
    apisecret = update.message.text
    context.user_data[DATA_MAIN_API_SECRET] = apisecret
    text = "Great, the main account is set. Now please write your sub account API Key"
    send_message(update, context, text)
    return SUB_API_KEY

def set_sub_api_key(update: Update, context: CallbackContext) -> int:
    subapikey = update.message.text
    context.user_data[DATA_SUB_API_KEY] = subapikey
    text = "And now please write the sub account API Secret"
    send_message(update, context, text)
    return SUB_API_SECRET

def set_sub_api_secret(update: Update, context: CallbackContext) -> int:
    subapisecret = update.message.text
    context.user_data[DATA_SUB_API_SECRET] = subapisecret
    text = "We are almost done, let's also set the sub account API Label"
    send_message(update, context, text)
    return SUB_API_LABEL

def set_sub_api_label(update: Update, context: CallbackContext) -> int:
    subapilabel = update.message.text
    context.user_data[DATA_SUB_API_LABEL] = subapilabel
    text = "Perfect, your dcaboost account is setup. As a last step, I am going test it to ensure everything works fine. Please wait few seconds."
    send_message(update, context, text)
    text = "Testing connection for\n"
    text = text + "Main API Key: " + mask(context.user_data[DATA_MAIN_API_KEY]) + "\n"
    text = text + "Main API Secret: " + mask(context.user_data[DATA_MAIN_API_SECRET]) + "\n"
    text = text + "Subaccount API Key: " + mask(context.user_data[DATA_SUB_API_KEY]) + "\n"
    text = text + "Subaccount API Secret: " + mask(context.user_data[DATA_SUB_API_SECRET]) + "\n"
    text = text + "Subaccount API Label: " + context.user_data[DATA_SUB_API_LABEL] + "\n"
    send_message(update, context, text)
    test_result = test_api(update.effective_chat.id, context.user_data[DATA_MAIN_API_KEY], context.user_data[DATA_MAIN_API_SECRET], context.user_data[DATA_SUB_API_KEY], context.user_data[DATA_SUB_API_SECRET],  context.user_data[DATA_SUB_API_LABEL])
    if test_result["test_result"]:
        text = "Perfect, the setup is completed. You are now ready to configure your recurrent crypto purchase. Just send /mydca once you're ready."
        save_account(update.effective_chat.id, context.user_data[DATA_MAIN_API_KEY], context.user_data[DATA_MAIN_API_SECRET], context.user_data[DATA_SUB_API_KEY], context.user_data[DATA_SUB_API_SECRET],  context.user_data[DATA_SUB_API_LABEL])
        send_message(update, context, text)
    else:
        text = "Sorry, there is an issue with your account setup. I was " + test_result["text"] + ". Please check your data again and repeat the /setup of your account"
        send_message(update, context, text)
    return ConversationHandler.END

def my_dca(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    text = ""
    account = get_account(chat_id)
    if not account:
        text = "You don't have an account setup yet. Please /setup your account first"
    else:
        current_dca = account[DATA_DCA_CONFIG]
        if current_dca:
            text = "You already have the following DCA setup:\n"
            for dca in current_dca:
                text = text + dca_to_text(dca) + "\n"
        else:
            text = "You have no DCA strategy setup yet\n"
        text = text + "\nTo add a new DCA strategy, please send /adddca command along with:\n"
        text = text + "1. The currency you want to pay with\n"
        text = text + "2. The crypto you want to buy\n"
        text = text + "3. The amount you want to invest\n"
        text = text + "4. The frequency of your investment\n"
        text = text + "Each value has to be separated by a space. The frequency can be DAILY, WEEKLY or BI-WEEKLY.\n"
        text = text + "For example, write /adddca USDC BTC 10 BI-WEEKLY if you want to buy 10 USDC of BTC every two weeks\n\n"
        text = text + "If you want to remove a DCA strategy, please send /removedca command with the base and crypto currencies of DCA you want to remove, separated by space.\n"
        text = text + "For example, write /removedca USDC BTC if you want to remove your DCA strategy of buying BTC with USDC\n\n"
    send_message(update, context, text)

def add_dca(update: Update, context: CallbackContext) -> None:
    new_dca = {}
    dca_value = context.args
    text = ""
    chat_id = update.effective_chat.id
    account = get_account(chat_id)
    if account:
        if dca_value and len(dca_value) == 4:
            base = str(dca_value[0]).upper()
            crypto = str(dca_value[1]).upper()
            frequency = str(dca_value[3]).upper()
            if str(dca_value[2]).isnumeric():
                amount = int(dca_value[2])
                if amount >= 1:
                    if frequency in FREQUENCIES:
                        instrument = get_instrument(crypto, base)
                        if instrument:
                            current_dca = account[DATA_DCA_CONFIG]
                            for existing_dca in current_dca:
                                if crypto == existing_dca[CRYPTO_CURRENCY_KEY] and base == existing_dca[BASE_CURRENCY_KEY]:
                                    text = "You have already set up a DCA strategy with these currencies. Please remove the existing one first with /deletedca if you want to change the values"
                            if text == "":
                                new_dca[FREQUENCY_IN_HOUR_KEY] = calculate_frequency_in_hours(frequency)
                                new_dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY] = amount
                                new_dca[CRYPTO_CURRENCY_KEY] = crypto
                                new_dca[BASE_CURRENCY_KEY] = base
                                current_dca.append(new_dca)
                                save_account(chat_id, account)
                                text = "Great, your new DCA strategy has been added"
                        else:
                            text = "The currency pair " + crypto + "/" + base + " is not yet supported"
                    else:
                        text = "Frequency must be daily or weekly"
                else:
                    text = "The amount has to be greater than 1"
            else:
                text = "The amount has to be a number without decimals"
        else:
            text = "You have to write exactly four values, separated by space"
    else:
        text = "You don't have an account setup yet. Please /setup your account first"
    send_message(update, context, text)

def unknown(update: Update, context: CallbackContext) -> None:
    text = "Sorry, I didn't understand that command"
    send_message(update, context, text)

def error_handler(update: object, context: CallbackContext) -> None:
    text = "An error occurred, DCA engine has been stopped. Please restart it manually with /startengine\n" \
        "Error details: " + context.error + "\n"
    if isinstance(update, Update):
        text = text + str(update.to_dict()) 
        send_message(update, context, text[:MAX_MESSAGE_LENGTH])
        stop_engine(update, context)
    else:
        text = text + str(update)
        telegram_settings = get_telegram_settings()
        chat_id = telegram_settings[ERROR_HANDLER_ID]
        context.bot.send_message(chat_id=chat_id, text=text[:MAX_MESSAGE_LENGTH])

def dca_to_text(dca: dict) -> str:
    text = "Buy " + str(dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]) + " " + dca[BASE_CURRENCY_KEY] + " of " + dca[CRYPTO_CURRENCY_KEY] + " every "
    if dca[FREQUENCY_IN_HOUR_KEY] == 1:
        text = text + "hour"
    elif dca[FREQUENCY_IN_HOUR_KEY] == 24:
        text = text + "day"
    elif dca[FREQUENCY_IN_HOUR_KEY] == 168:
        text = text + "week"
    else:
        text = text + amount_format(int(dca[FREQUENCY_IN_HOUR_KEY]*60)) + " minutes"
    return text

def calculate_frequency_in_hours(frequency: str) -> int:
    result = 1
    if(frequency == DAILY_FREQUENCE):
        result = 24
    elif(frequency == WEEKLY_FREQUENCE):
        result = 24*7
    elif(frequency == BI_WEEKLY_FREQUENCE):
        result = 24*14
    return result

def start_engine(update: Update, context: CallbackContext) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        global RUNNING_ENGINES
        if not RUNNING_ENGINES or not RUNNING_ENGINES[client_id] or RUNNING_ENGINES[client_id].isSet():
            RUNNING_ENGINES[client_id] = threading.Event()
            text = "Trading engine correctly started"
            send_message(update, context, text)
            execute_trading_engine(update, context)
        else:
            text =  "Trading engine is already running"
            send_message(update, context, text)
    else:
        text = "You don't have an account yet. Please send /setup to create it"
        send_message(update, context, text)
    

def stop_engine(update: Update, context: CallbackContext) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        global RUNNING_ENGINES
        if RUNNING_ENGINES and RUNNING_ENGINES[client_id] and not RUNNING_ENGINES[client_id].isSet():
            RUNNING_ENGINES[client_id].set()
            text = "Trading engine stopped"
            time.sleep(1)
        else:
            text = "Trading engine already stopped"
    else:
        text = "You don't have an account yet. Please send /setup to create it"
    send_message(update, context, text)

def status(update: Update, context: CallbackContext) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        global RUNNING_ENGINES
        if RUNNING_ENGINES and RUNNING_ENGINES[client_id] and not RUNNING_ENGINES[client_id].isSet():
            text = "Trading engine is running"
        else:
            text = "Trading engine is not running"
    else:
        text = "You don't have an account yet. Please send /setup to create it"
    send_message(update, context, text)

def execute_trading_engine(update: Update, context: CallbackContext) -> None:
    settings = get_account(update.effective_chat.id)
    dca_settings = settings[DATA_DCA_CONFIG]
    if dca_settings:
        for dca in dca_settings:
            crypto = dca[CRYPTO_CURRENCY_KEY]
            base = dca[BASE_CURRENCY_KEY]
            buy_amount = dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]
            frequency = int(dca[FREQUENCY_IN_HOUR_KEY] * SECONDS_IN_ONE_HOUR)
            text = "Starting DCA on " + crypto + ", buying " + str(buy_amount) + " " + base + " every " + str(frequency) + " seconds"
            send_message(update, context, text)
            dca_thread = threading.Thread(target = execute_dca, args = (crypto, base, buy_amount, frequency, update, context), daemon = True)
            time.sleep(1)
            dca_thread.start()

def execute_dca(crypto: str, base: str, buy_amount: float, frequency: int, update: Update, context: CallbackContext):
    client_id = update.effective_chat.id
    settings = get_account(client_id)
    waiting_time = wait_time_from_last_trade(client_id, settings, crypto, base, frequency, 0, update, context)
    global RUNNING_ENGINES
    while not RUNNING_ENGINES[client_id].wait(timeout = waiting_time):
        time_offset = time.time()
        message = transfer_to_sub_account(client_id, settings, buy_amount, base)
        if NEGATIVE_BALANCE in str(message):
            text = "You have less than " + str(buy_amount) + " " + base + " available to buy " + crypto + ". Trying again in " + str(int(frequency)) + " seconds"
            send_message(update, context, text)
            waiting_time = int(frequency)
        else:
            text = "Buying " + str(buy_amount) + " " + base + " of " + crypto
            send_message(update, context, text)
            create_buy_order(client_id, settings, crypto, base, buy_amount)
            time_offset = time.time()-time_offset
            text = transfer_to_master_account(client_id, settings, crypto)
            send_message(update, context, text)
            text = transfer_to_master_account(client_id, settings, base)
            send_message(update, context, text)
        settings = get_account(client_id)
        waiting_time = wait_time_from_last_trade(client_id, settings, crypto, base, frequency, time_offset, update, context)
    text = "Stopping DCA on " + crypto + "/" + base
    send_message(update, context, text)

credentials = get_telegram_settings()
tokenData = credentials[BOT_TOKEN_KEY]
updater = Updater(token=tokenData)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
setup_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup)],
        states={
            MAIN_API_KEY: [MessageHandler(Filters.text, set_main_api_key)],
            MAIN_API_SECRET: [MessageHandler(Filters.text, set_main_api_secret)],
            SUB_API_KEY: [MessageHandler(Filters.text, set_sub_api_key)],
            SUB_API_SECRET: [MessageHandler(Filters.text, set_sub_api_secret)],
            SUB_API_LABEL: [MessageHandler(Filters.text, set_sub_api_label)]
        },
        fallbacks=[]
    )
my_dca_handler = CommandHandler('mydca', my_dca)
add_dca_handler = CommandHandler('adddca', add_dca)
help_handler = CommandHandler('help', help)
start_engine_handler = CommandHandler('startengine', start_engine)
stop_engine_handler = CommandHandler('stopengine', stop_engine)
status_handler = CommandHandler('status', status)
unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(setup_handler)
dispatcher.add_handler(my_dca_handler)
dispatcher.add_handler(add_dca_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(start_engine_handler)
dispatcher.add_handler(stop_engine_handler)
dispatcher.add_handler(status_handler)
dispatcher.add_handler(unknown_handler)
dispatcher.add_error_handler(error_handler)
updater.start_polling()
updater.idle()