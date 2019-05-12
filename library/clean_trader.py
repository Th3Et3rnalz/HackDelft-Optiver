from server_interface import ServerInterface
import numpy as np
import time
interface = ServerInterface()
name = "cookie_sophisticated_2"

percentage_bought_threshold = 0.7
risk_factor = 0.2

current_market = {
    "SP-FUTURE": None,
    "ESX-FUTURE": None
}

old_market = {
    "SP-FUTURE": None,
    "ESX-FUTURE": None
}
trade = None

def callback(entry):
    global trade

    #print(entry)
    if entry['TYPE'] == 'PRICE':
        #print(trade)
        # Update market variables
        old_market[entry['FEEDCODE']] = current_market[entry['FEEDCODE']]
        current_market[entry['FEEDCODE']] = entry

        # Check if data available
        for key in old_market.keys():
            if old_market[key] is None:
                print("returning")
                return


        # Start trade
        # Switch feedcode
        feedcode = "ESX-FUTURE"
        if trade['FEEDCODE'] == 'ESX-FUTURE':
            feedcode = "SP-FUTURE"

        if trade['SIDE'] == 'BID':
            #print("Received bid")
            # Received trade is BID so BUY
            percentage_bought = float(trade['VOLUME']) / float(current_market[trade['FEEDCODE']]['BID_VOLUME'])

            percentage_bought_factor = 0.
            if percentage_bought > percentage_bought_threshold:
                percentage_bought_factor = (percentage_bought - percentage_bought_threshold)/(1. - percentage_bought_threshold)

            # TODO: Risk analysis
            trade_volume_factor = float(trade['VOLUME']) / 500

            price_difference = float(current_market[feedcode]['ASK_PRICE']) - float(old_market[feedcode]['ASK_PRICE'])
            price_difference_factor = 0
            if price_difference < - 0.5:
                price_difference_factor = -price_difference

            amount = np.ceil(risk_factor * float(current_market[feedcode]['ASK_VOLUME']) * percentage_bought_factor * trade_volume_factor * price_difference_factor).astype(int)

            if amount > 0:
                interface.buy(name, feedcode, 100000, amount)
        else:
            # Received trade is ASK so SELL
            percentage_bought = float(trade['VOLUME']) / float(current_market[trade['FEEDCODE']]['ASK_VOLUME'])

            percentage_bought_factor = 0.
            if percentage_bought > percentage_bought_threshold:
                percentage_bought_factor = (percentage_bought - percentage_bought_threshold)/(1. - percentage_bought_threshold)

            # TODO: Risk analysis
            trade_volume_factor = float(trade['VOLUME']) / 500

            price_difference = float(current_market[feedcode]['ASK_PRICE']) - float(old_market[feedcode]['ASK_PRICE'])
            price_difference_factor = 0
            if price_difference > 0.5:
                price_difference_factor = price_difference

            amount = np.ceil(risk_factor * float(current_market[feedcode]['BID_VOLUME']) * percentage_bought_factor * trade_volume_factor * price_difference_factor).astype(int)

            if amount > 0:
                interface.sell(name, feedcode, 1, amount)

    if entry['TYPE'] == 'TRADE':
        trade = entry


interface.register_callback(callback)
interface.start_listen()
