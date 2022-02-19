from decimal import ROUND_DOWN
from dcaboostutils import DATA_MAIN_API_KEY, DATA_MAIN_API_SECRET, DATA_SUB_API_KEY, DATA_SUB_API_SECRET, Decimal, json, time, query, create_pair, amount_format, get_current_subaccount, send_message

LOCK_QUERY_ACTIVE = 0

MASTER_ACCOUNT = "MASTER"
SUB_ACCOUNT = "SUBACCOUNT"

CRYPTO_CURRENCY_KEY = "CRYPTO_CURRENCY"
BASE_CURRENCY_KEY = "BASE_CURRENCY"
BUY_AMOUNT_IN_BASE_CURRENCY_KEY = "BUY_AMOUNT_IN_BASE_CURRENCY"
FREQUENCY_IN_HOUR_KEY = "FREQUENCY_IN_HOUR"
SECONDS_IN_ONE_HOUR = 3600

def get_account_summary(client_id, apikey, apisecret, currency = None):
    method = "private/get-account-summary"
    params = {}
    if currency:
        params["currency"] = currency
    result = query(client_id, apikey, apisecret, method, params)
    return json.loads(result.text)

def get_available_quantity(client_id, apikey, apisecret, currency):
    summary = get_account_summary(client_id, apikey, apisecret, currency)
    available = 0
    if summary and summary["result"] and summary["result"]["accounts"]:
        available = summary["result"]["accounts"][0]["available"]
    return_value = Decimal(str(available))
    if return_value.as_tuple().exponent < -8:
        return_value = Decimal(str(available)).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    return return_value

def get_sub_account_uuid(client_id):
    sub_account_uuid = None
    sub_account = get_current_subaccount(client_id)
    if sub_account:
        sub_account_uuid = sub_account["uuid"]
    return sub_account_uuid

def transfer_amount(client_id, apikey, apisecret, from_account, to_account, amount, currency):
    json_result = None
    if amount>0:
        method = "private/subaccount/transfer"
        params = {
            "from": from_account,
            "to": to_account,
            "sub_account_uuid": get_sub_account_uuid(client_id),
            "currency": currency,
            "amount": str(amount)
            }
        query_result = query(client_id, apikey, apisecret, method, params)
        if query_result is not None:
            json_result = json.loads(query_result.text)
    return json_result

def create_buy_order(client_id, settings, crypto, base, buy_amount):
    json_result = None
    method = "private/create-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "side": "BUY",
        "type": "MARKET",
        "notional": buy_amount
        }
    query_result = query(client_id, settings[DATA_SUB_API_KEY], settings[DATA_SUB_API_SECRET], method, params)
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

def get_trades(client_id, apikey, apisecret, crypto, base, start_time, end_time = None):
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
                result = query(client_id, apikey, apisecret, method, params)
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

def transfer_to_master_account(client_id, settings, currency):
    text = ""
    apikey = settings[DATA_SUB_API_KEY]
    apisecret = settings[DATA_SUB_API_SECRET]
    available_quantity = get_available_quantity(client_id, apikey, apisecret, currency)
    if available_quantity > 0:
        transfer_amount(client_id, apikey, apisecret, SUB_ACCOUNT, MASTER_ACCOUNT, available_quantity, currency)
        text = "Transfering " + amount_format(available_quantity) + " " + currency + " from " + SUB_ACCOUNT
    else:
        text = "No " + currency + " available for transfer from " + SUB_ACCOUNT
    return text

def transfer_to_sub_account(client_id, settings, amount, currency):
    text = transfer_amount(client_id, settings[DATA_MAIN_API_KEY], settings[DATA_MAIN_API_SECRET], MASTER_ACCOUNT, SUB_ACCOUNT, amount, currency)
    return text

def wait_from_last_trade(client_id, settings, crypto, base, frequency, update, context):
    expected_last_trade = (int(time.time()) - frequency) * 1000
    time_until_next_trade = frequency
    trades = get_trades(client_id, settings[DATA_SUB_API_KEY], settings[DATA_SUB_API_SECRET], crypto, base, expected_last_trade)
    if trades:
        most_recent_trade = 0
        for trade in trades:
            if most_recent_trade < trade["create_time"]:
                most_recent_trade = trade["create_time"]
        time_until_next_trade = int((most_recent_trade + frequency*1000 - int(time.time()*1000))/1000)
    elif trades is not None:
        time_until_next_trade = 1
    text = "Waiting " + str(time_until_next_trade) + " seconds before next buy order of " + crypto + " is placed"
    if time_until_next_trade == 1:
        text = "Buying " + crypto + " immediately"
    send_message(update, context, text)
    time.sleep(time_until_next_trade-3)