# dca-boost

A python tool to set a [Dollar Cost Averaging](https://en.wikipedia.org/wiki/Dollar_cost_averaging) strategy through [Crypto.com Exchange](crypto.com/exchange)

## How to use dca-boost:

### Before starting

#### Install dependencies
- python-telegram-bot (pip install python-telegram-bot)

dca-boost requires Python > 3.0. It has been tested with Python 3.7

#### Configure the tool with your [Crypto.com Exchange](crypto.com/exchange) API key
1. You need to rename the file settings.json.sample into settings.json
2. You need to activate and control dca-boost via a telegram bot. To do that, you need to put your own TelegramBotToken into settings.json file. To know how to define a bot, please follow the official guide here: [https://core.telegram.org/bots#6-botfather](https://core.telegram.org/bots#6-botfather)
3. You need to setup your own [Crypto.com Exchange](crypto.com/exchange) APIKey and APISecret, for your main account, and you'll have to setup a dedicated subaccount with its own APIKey and APISecret. To know how to create an API key, please follow the official guide [https://exchange-docs.crypto.com/spot/index.html#generating-the-api-key](https://exchange-docs.crypto.com/spot/index.html#generating-the-api-key)

### Running the trading engine

To start dca-boost just run: python3 dcaboostgram.py


#### Features

The following commands are currently implemented:

```
setup - to setup your account
mydca - to display your DCA strategy
adddca - to add a new DCA strategy to your account
removedca - to remove one DCA strategy from your account
status - to check the trading engine status
startengine - to start the trading engine
stopengine - to stop the trading engine
deleteaccount - to delete your account
```
