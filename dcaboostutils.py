import json
import hmac
import hashlib
import time
import requests
import urllib
from decimal import Decimal

BASE_URI = "https://api.crypto.com/v2/"
SETTINGS_FILE = "settings.json"
API_KEY = "APIKey"
API_SECRET = "APISecret"
MAIN_API_KEY = "MainAPIKey"
MAIN_API_SECRET = "MainAPISecret"
MAX_MESSAGE_LENGTH = 4096

def create_pair(crypto, base):
    return crypto + "_" + base

def get_ratio(currentValue, minValue, maxValue):
    #Calculate the relative value of currentValue between min and max, where the output if current = min is 1 and if current = max is 0
    return Decimal(1 - ((Decimal(currentValue)-Decimal(minValue))/(Decimal(maxValue)-Decimal(minValue))))

def get_settings():
    return get_json_data(SETTINGS_FILE)

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

def query(method, params={}, apikey = None, apisecret = None):
    time.sleep(1)
    credentials = get_json_data(SETTINGS_FILE)
    if not apikey:
        apikey = credentials[API_KEY]
    if not apisecret:
        apisecret = credentials[API_SECRET]
    req = {
        "id" : 1,
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

def query_main(method, params = {}):
    credentials = get_json_data(SETTINGS_FILE)
    apikey = credentials[MAIN_API_KEY]
    apisecret = credentials[MAIN_API_SECRET]
    return query(method, params,apikey, apisecret)

def public_query(method, params={}):
    time.sleep(1)
    paramsList = urllib.parse.urlencode(params)
    return requests.get(BASE_URI + method + "?" + paramsList)

def amount_format(value):
    return '{0:f}'.format(Decimal(str(value)))

def get_account_summary_text(currency = None):
    result = get_account_summary(currency)
    output = ""
    if result and result["result"]:
        accounts = result["result"]["accounts"]
        for account in accounts:
            if account["balance"] != 0:
                output = output + amount_format(account["balance"]) + " " + account["currency"] + " (" + amount_format(account["available"]) + " available, " + amount_format(account["order"]) + " in order)" +"\n"
    if output == "":
        altText = "active balance"
        if currency:
            altText = currency
        output = "You don't have any " + altText
    return output

def get_account_summary(currency = None):
    method = "private/get-account-summary"
    params = {}
    if currency:
        params["currency"] = currency
    result = query(method, params)
    return json.loads(result.text)