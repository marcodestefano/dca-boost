import os
import threading
import traceback
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
from dcaboostutils import DATA_MAIN_API_KEY, DATA_MAIN_API_SECRET, DATA_SUB_API_KEY, DATA_SUB_API_SECRET, DATA_SUB_API_LABEL, DATA_DCA_CONFIG, DATA_DCA_RUNNING, time, save_account, get_telegram_settings, get_account, send_message, test_api, get_instrument, mask
from dcaboost import CRYPTO_CURRENCY_KEY, BASE_CURRENCY_KEY, BUY_AMOUNT_IN_BASE_CURRENCY_KEY, FREQUENCY_IN_HOUR_KEY, SECONDS_IN_ONE_HOUR, transfer_to_master_account, transfer_to_sub_account, wait_from_last_trade, create_buy_order

BOT_TOKEN_KEY = 'TelegramBotToken'
NEGATIVE_BALANCE = "NEGATIVE_BALANCE"
DCA_THREADS = {}

HOURLY_FREQUENCE = "HOURLY"
DAILY_FREQUENCE = "DAILY"
WEEKLY_FREQUENCE = "WEEKLY"
FREQUENCIES = [HOURLY_FREQUENCE, DAILY_FREQUENCE, WEEKLY_FREQUENCE]

MAIN_API_KEY, MAIN_API_SECRET, SUB_API_KEY, SUB_API_SECRET, SUB_API_LABEL = range(5)
DCA_SETTINGS = range(1)

def start(update, context):
    first_name = update.effective_chat.first_name
    if not first_name:
        first_name = ""
    bot = context.bot
    chat_id = update.effective_chat.id
    text = "Welcome to dcaboost, " + first_name + "! Use /setup to setup your account"
    if get_account(chat_id):
        text = "Welcome back to dcaboost, " + first_name + "! You already have an account, use /help to display the available commands"
    bot.send_message(chat_id=chat_id, text=text)

def help(update, context) -> None:
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

def setup(update, context):
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
    update.message.reply_text(text)
    return conversation_next_step

def set_main_api_key(update, context):
    apikey = update.message.text
    context.user_data[DATA_MAIN_API_KEY] = apikey
    text = "Ok, now please write your main account API Secret"
    update.message.reply_text(text)
    return MAIN_API_SECRET

def set_main_api_secret(update, context):
    apisecret = update.message.text
    context.user_data[DATA_MAIN_API_SECRET] = apisecret
    text = "Great, the main account is set. Now please write your sub account API Key"
    update.message.reply_text(text)
    return SUB_API_KEY

def set_sub_api_key(update, context):
    subapikey = update.message.text
    context.user_data[DATA_SUB_API_KEY] = subapikey
    text = "And now please write the sub account API Secret"
    update.message.reply_text(text)
    return SUB_API_SECRET

def set_sub_api_secret(update, context):
    subapisecret = update.message.text
    context.user_data[DATA_SUB_API_SECRET] = subapisecret
    text = "We are almost done, let's also set the sub account API Label"
    update.message.reply_text(text)
    return SUB_API_LABEL

def set_sub_api_label(update, context):
    subapilabel = update.message.text
    context.user_data[DATA_SUB_API_LABEL] = subapilabel
    text = "Perfect, your dcaboost account is setup. As a last step, I am going test it to ensure everything works fine. Please wait few seconds."
    update.message.reply_text(text)
    text = "Testing connection for\n"
    text = text + "Main API Key: " + mask(context.user_data[DATA_MAIN_API_KEY]) + "\n"
    text = text + "Main API Secret: " + mask(context.user_data[DATA_MAIN_API_SECRET]) + "\n"
    text = text + "Subaccount API Key: " + mask(context.user_data[DATA_SUB_API_KEY]) + "\n"
    text = text + "Subaccount API Secret: " + mask(context.user_data[DATA_SUB_API_SECRET]) + "\n"
    text = text + "Subaccount API Label: " + context.user_data[DATA_SUB_API_LABEL] + "\n"
    update.message.reply_text(text)
    test_result = test_api(update.effective_chat.id, context.user_data[DATA_MAIN_API_KEY], context.user_data[DATA_MAIN_API_SECRET], context.user_data[DATA_SUB_API_KEY], context.user_data[DATA_SUB_API_SECRET],  context.user_data[DATA_SUB_API_LABEL])
    if test_result["test_result"]:
        text = "Perfect, the setup is completed. You are now ready to configure your recurrent crypto purchase. Just send /mydca once you're ready."
        save_account(update.effective_chat.id, context.user_data[DATA_MAIN_API_KEY], context.user_data[DATA_MAIN_API_SECRET], context.user_data[DATA_SUB_API_KEY], context.user_data[DATA_SUB_API_SECRET],  context.user_data[DATA_SUB_API_LABEL])
        update.message.reply_text(text)
    else:
        text = "Sorry, there is an issue with your account setup. I was " + test_result["text"] + ". Please check your data again and repeat the /setup of your account"
        update.message.reply_text(text)
    return ConversationHandler.END

def my_dca(update, context):
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
        text = text + "Each value has to be separated by a space. The frequency can be daily or weekly.\n"
        text = text + "For example, write /adddca USDC BTC 10 WEEKLY if you want to buy 10 USDC of BTC every week\n\n"
        text = text + "If you want to remove a DCA strategy, please send /removedca command with the base and crypto currencies of DCA you want to remove, separated by space.\n"
        text = text + "For example, write /removedca USDC BTC if you want to remove your DCA strategy of buying BTC with USDC\n\n"
    update.message.reply_text(text)

def add_dca(update, context):
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
    update.message.reply_text(text)

def dca_to_text(dca) -> str:
    text = "Buy " + str(dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]) + " " + dca[BASE_CURRENCY_KEY] + " of " + dca[CRYPTO_CURRENCY_KEY] + " every "
    if dca[FREQUENCY_IN_HOUR_KEY] == 1:
        text = text + "hour"
    elif dca[FREQUENCY_IN_HOUR_KEY] == 24:
        text = text + "day"
    elif dca[FREQUENCY_IN_HOUR_KEY] == 168:
        text = text + "week"
    return text

def calculate_frequency_in_hours(frequency) -> int:
    result = 1
    if(frequency == DAILY_FREQUENCE):
        result = 24
    elif(frequency == WEEKLY_FREQUENCE):
        result = 24*7
    return result

def cancel(update, context):
    text = "All right, setup canceled."
    update.message.reply_text(text)
    return ConversationHandler.END

def unknown(update, context) -> None:
    text = "Sorry, I didn't understand that command"
    send_message(update, context, text)

def start_engine(update, context) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        trading_engine_active = account[DATA_DCA_RUNNING]
        if not trading_engine_active:
            account[DATA_DCA_RUNNING] = True
            save_account(client_id, account)
            tradingEngineThread = threading.Thread(target = execute_trading_engine, args = [update, context])
            global DCA_THREADS
            DCA_THREADS[client_id] = tradingEngineThread
            tradingEngineThread.start()
            text = "Trading engine correctly started"
        else:
            text =  "Trading engine is already running"
    else:
        text = "You don't have an account yet. Please send /setup to create it"
    send_message(update, context, text)

def stop_engine(update, context) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        trading_engine_active = account[DATA_DCA_RUNNING]
        if trading_engine_active:
            account[DATA_DCA_RUNNING] = False
            save_account(client_id, account)
            global DCA_THREADS
            if DCA_THREADS and DCA_THREADS[client_id]:
                DCA_THREADS[client_id].join()
            text = "Trading engine stopped"
        else:
            text = "Trading engine already stopped"
    else:
        text = "You don't have an account yet. Please send /setup to create it"
    send_message(update, context, text)

def status(update, context) -> None:
    text = ""
    client_id = update.effective_chat.id
    account = get_account(client_id)
    if account:
        trading_engine_active = account[DATA_DCA_RUNNING]
        if trading_engine_active:
            text = "Trading engine is running"
        else:
            text = "Trading engine is not running"
    else:
        text = "You don't have an account yet. Please send /setup to create it"
    send_message(update, context, text)

def execute_trading_engine(update, context) -> None:
    try:
        settings = get_account(update.effective_chat.id)
        dca_settings = settings[DATA_DCA_CONFIG]
        if dca_settings:
            for dca in dca_settings:
                crypto = dca[CRYPTO_CURRENCY_KEY]
                base = dca[BASE_CURRENCY_KEY]
                buy_amount = dca[BUY_AMOUNT_IN_BASE_CURRENCY_KEY]
                frequency = dca[FREQUENCY_IN_HOUR_KEY] * SECONDS_IN_ONE_HOUR
                text = "Starting DCA on " + crypto + ", buying " + str(buy_amount) + " " + base + " every " + str(frequency) + " seconds"
                send_message(update, context, text)
                dca_thread = threading.Thread(target = execute_dca, args = (crypto, base, buy_amount, frequency, update, context), daemon = True)
                time.sleep(1)
                dca_thread.start()
    except Exception:
        text = "An error occurred"
        send_message(update, context, text)
        stop_engine(update, context)
        text = time.strftime("%Y-%m-%d %H:%M:%S") + " Error in the execution of the engine: " + str(traceback.print_exc())
        start_engine(update, context)
    return

def execute_dca(crypto, base, buy_amount, frequency, update, context):
    client_id = update.effective_chat.id
    settings = get_account(client_id)
    while settings[DATA_DCA_RUNNING]:
        text = transfer_to_master_account(client_id, settings, crypto)
        send_message(update, context, text)
        text = transfer_to_master_account(client_id, settings, base)
        send_message(update, context, text)
        wait_from_last_trade(client_id, settings, crypto, base, frequency, update, context)
        message = transfer_to_sub_account(client_id, settings, buy_amount, base)
        if NEGATIVE_BALANCE in str(message):
            text = "You have less than " + str(buy_amount) + " " + base + " available to buy " + crypto + ". Trying again in " + str(int(frequency/4)) + " seconds"
            send_message(update, context, text)
            time.sleep(int(frequency/4))
        else:
            text = "Buying " + str(buy_amount) + " " + base + " of " + crypto
            send_message(update, context, text)
            create_buy_order(client_id, settings, crypto, base, buy_amount)
    settings = get_account(client_id)

def start_active_dcas() -> None:
    return

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
        fallbacks=[CommandHandler('cancel', cancel)]
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
start_active_dcas()
updater.start_polling()
updater.idle()