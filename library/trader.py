from trader_class import Trader
import numpy as np
import time
name = "baas-2"

trades = 0
def callback(trader, entry):
    global trades
    if entry['TYPE'] == 'TRADE':
        feedcode = "ESX-FUTURE"
        if entry['FEEDCODE'] == 'ESX-FUTURE':
            feedcode = "SP-FUTURE"

        if entry['SIDE'] == 'BID':
            trader.sell(feedcode, min(np.ceil(int(entry['VOLUME'])).astype(int),300))
        else:
            trader.buy(feedcode, min(np.ceil(int(entry['VOLUME'])).astype(int),300))
        trades +=1
        if trades % 300 == 0:
            print("RESETTING POSITIONS")
            trader.reset_positions()
trader = Trader(name, callback)
trader.start_trading()
