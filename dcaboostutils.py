import json
import os
import hmac
import hashlib
import time
import requests
import urllib
from decimal import ROUND_DOWN, Decimal

BASE_URI = "https://api.crypto.com/v2/"
SETTINGS_FILE = "settings.json"

DATA_MAIN_API_KEY = "MainAPIKey"
DATA_MAIN_API_SECRET = "MainAPISecret"
DATA_SUB_API_KEY = "SubAccountAPIKey"
DATA_SUB_API_SECRET = "SubAccountAPISecret"
DATA_SUB_API_LABEL = "SubAccountAPILabel"
DATA_DCA_CONFIG = "DCA"

def send_message(update, context, text) -> None:
    context.bot.send_message(chat_id = update.effective_chat.id, text=text)

def create_pair(crypto, base) -> str:
    return crypto + "_" + base

def get_telegram_settings():
    return get_json_data(SETTINGS_FILE)

def delete_account_data(client_id) -> None:
    filename = get_filename(client_id)
    if os.path.isfile(filename):
        os.remove(filename)

def get_filename(client_id) -> str:
    return str(client_id) + "_" + SETTINGS_FILE

def get_account(client_id) -> dict:
    filename = get_filename(client_id)
    content = {}
    try:
        content = get_json_data(filename)
    except FileNotFoundError:
        content = None
    return content

def get_json_data(filename):
    with open(filename) as keys:
        content = json.load(keys)
    return content

def params_to_str(obj, level):
    MAX_LEVEL = 3
    if level >= MAX_LEVEL:
        return str(obj)

    return_str = ""
    for key in sorted(obj):
        return_str += key
        if isinstance(obj[key], list):
            for subObj in obj[key]:
                return_str += params_to_str(subObj, ++level)
        else:
            return_str += str(obj[key])
    return return_str

def query(client_id, apikey, apisecret, method, params={}):
    req = {
        "id" : client_id,
        "method": method,
        "api_key": apikey,
        "params" : params,
        "nonce": int(time.time() * 1000)
    }
    param_str = "" 
    if "params" in req:
        param_str = params_to_str(req['params'], 0)
    payload_str = req['method'] + str(req['id']) + req['api_key'] + param_str + str(req['nonce'])
    req['sig'] = hmac.new(
        bytes(str(apisecret), 'utf-8'),
        msg=bytes(payload_str, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return requests.post(BASE_URI + method, json=req, headers={'Content-Type':'application/json'})

def public_query(method, params={}):
    paramsList = urllib.parse.urlencode(params)
    return requests.get(BASE_URI + method + "?" + paramsList)

def save_account(client_id, main_api_key, main_api_secret, sub_api_key, sub_api_secret, sub_api_label, dca_config = []) -> dict:
    user_data = {
        DATA_MAIN_API_KEY : main_api_key,
        DATA_MAIN_API_SECRET: main_api_secret,
        DATA_SUB_API_KEY: sub_api_key,
        DATA_SUB_API_SECRET: sub_api_secret,
        DATA_SUB_API_LABEL : sub_api_label,
        DATA_DCA_CONFIG: dca_config
    }
    return save_account(client_id, user_data)

def save_account(client_id, user_data):
    filename = get_filename(client_id)
    with open(filename, 'w') as outfile:
        json.dump(user_data, outfile)
    return user_data

def test_api(client_id, main_api_key, main_api_secret, sub_api_key, sub_api_secret, sub_api_label) -> dict:
    final_result = True
    text = ""
    main_account_result = get_account_summary(client_id, main_api_key, main_api_secret)
    if not main_account_result or main_account_result["code"] != 0:
        final_result = False
        text = "unable to connect to the main account"
    if final_result:
        sub_account_result = get_account_summary(client_id, sub_api_key, sub_api_secret)
        if not sub_account_result or sub_account_result["code"] != 0:
            final_result = False
            text = "unable to connect to the subaccount"
    if final_result:
        main_subaccounts = get_sub_accounts(client_id, main_api_key, main_api_secret)
        if not main_subaccounts or not main_subaccounts["result"] or not main_subaccounts["result"]["sub_account_list"]:
            final_result = False
        else:
            exist_subaccount = False
            for subaccount in main_subaccounts["result"]["sub_account_list"]:
                if subaccount["label"] == sub_api_label:
                    exist_subaccount = True
            if not exist_subaccount:
                final_result = False
        if not final_result:
            text = "unable to find the specified subaccount under main account"
    result = {}
    result["test_result"] = final_result
    result["text"] = text
    return result
    
def mask(value_to_mask) -> str:
    return_value = "********"
    if value_to_mask and len(value_to_mask)>8:
        return_value = value_to_mask[:4] + return_value + value_to_mask[len(value_to_mask)-4:]
    return return_value

def amount_format(value):
    return_value = Decimal(str(value))
    if return_value.as_tuple().exponent < -8:
        return_value = Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    return '{0:f}'.format(return_value)

def get_account_summary_text(currency = None):
    result = get_account_summary(currency)
    output = ""
    if result and result["result"]:
        accounts = result["result"]["accounts"]
        for account in accounts:
            decimal_amount = amount_format(account["balance"])
            if Decimal(decimal_amount) > 0:
                output = output + amount_format(account["balance"]) + " " + account["currency"] + " (" + amount_format(account["available"]) + " available, " + amount_format(account["order"]) + " in order)" +"\n"
    if output == "":
        altText = "active balance"
        if currency:
            altText = currency
        output = "You don't have any " + altText
    return output

def get_current_subaccount(client_id):
    account = get_account(client_id)
    result = None
    if account:
        account_label = account[DATA_SUB_API_LABEL]
        sub_accounts = get_sub_accounts(client_id, account)
        if sub_accounts and sub_accounts["result"]:
            for sub_account in sub_accounts["result"]["sub_account_list"]:
                if sub_account["label"] == account_label:
                    result = sub_account
                    break
    return result

def get_sub_accounts(client_id, apikey, apisecret):
    method = "private/subaccount/get-sub-accounts"
    params = {
        }
    result = query(client_id, apikey, apisecret, method, params)
    return json.loads(result.text)

def get_account_summary(client_id, apikey, apisecret, currency = None):
    method = "private/get-account-summary"
    params = {}
    if currency:
        params["currency"] = currency
    result = query(client_id, apikey, apisecret, method, params)
    return json.loads(result.text)

def get_sub_accounts(client_id, account):
    json_result = None
    method = "private/subaccount/get-sub-accounts"
    params = {
        }
    apikey = account[DATA_MAIN_API_KEY]
    apisecret = account[DATA_MAIN_API_SECRET]
    query_result = query(client_id, apikey, apisecret, method, params)
    if query_result:
        json_result = json.loads(query_result.text)
    return json_result

def get_instrument(crypto,base):
    method = "public/get-instruments"
    result = public_query(method)
    json_result = json.loads(result.text)
    instrument_result = None
    if (json_result and json_result["result"]):
        for instrument in json_result["result"]["instruments"]:
            if instrument["quote_currency"] == base and instrument["base_currency"] == crypto:
                instrument_result = instrument
    return instrument_result