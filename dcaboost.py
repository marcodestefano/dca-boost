import threading
import traceback
from dcaboostutils import json, time, query, create_pair, get_settings

TRADING_ENGINE_ACTIVE = 0

CRYPTO_CURRENCY_KEY = "CRYPTO_CURRENCY"
BASE_CURRENCY_KEY = "BASE_CURRENCY"
BUY_AMOUNT_IN_BASE_CURRENCY_KEY = "BUY_AMOUNT_IN_BASE_CURRENCY"
FREQUENCY_IN_HOUR_KEY = "FREQUENCY_IN_HOUR"
SECONDS_IN_ONE_HOUR = 60*60

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