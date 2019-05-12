from server_interface import ServerInterface
import numpy as np
import time
interface = ServerInterface()
name = "cookie3"

def callback(entry):
    if entry['TYPE'] == 'TRADE':
        feedcode = "ESX-FUTURE"
        if entry['FEEDCODE'] == 'ESX-FUTURE':
            feedcode = "SP-FUTURE"

        if entry['SIDE'] == 'BID':
            print("selling")
            interface.sell(name, feedcode,  1000,np.ceil(int(entry['VOLUME'])).astype(int))
        else:
            print("buying")
            interface.buy(name, feedcode, 10000, np.ceil(int(entry['VOLUME'])).astype(int))
interface.register_callback(callback)
interface.start_listen()
