import numpy as np
np.set_printoptions(linewidth=200)
import matplotlib.pyplot as plt
import matplotlib.dates
import socket
import multiprocessing
import time
import pickle
import datetime

class ServerInterface:
    UDP_IP = "188.166.115.7"
    UDP_BROADCAST_PORT = 7001
    UDP_EXCHANGE_PORT = 8001
    HELLO_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST".encode("ascii")
    def __init__(self, should_print = False):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 8014))
        self.s.sendto(self.HELLO_MESSAGE, (self.UDP_IP, self.UDP_BROADCAST_PORT))
        self.listen_process = None
        self.product_monitor_processes = {}
        self.product_monitor_figures = []
        self.data_queue = None
        self._products = {}
        self.s_exchange = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_exchange.bind(("", 8093))
        self.s_exchange.settimeout(5.0)
        self._should_print = should_print

        self._callbacks = []

    def register_callback(self, fn):
        self._callbacks += [fn]
        print("callback_registered")

    @property
    def should_print(self):
        return self._should_print;
    def set_should_print(self, should_print):
        self._should_print = should_print

    def _listen_to_server(self):
        sock = self.s
        queue = self.data_queue
        while True:
            data, addr = sock.recvfrom(1024)
            msg = data.decode("ascii")
            properties = msg.split("|")
            entry = {}
            for p in properties:
                k,v = p.split("=")
                entry[k] = v
            entry['TIMESTAMP'] = datetime.datetime.now()
            queue.put(entry)
            if entry["TYPE"] == "ORDER_ACK":
                print(entry)
                end = True
            else:
                for fn in self._callbacks:
                    fn(entry)
                if self._should_print:
                    print('[{}] {}'.format(entry['TIMESTAMP'], entry))

    def _update_products(self):
        while not self.data_queue.empty():
            entry = self.data_queue.get_nowait()
            assert set(['TYPE','FEEDCODE','TIMESTAMP']) <= set(entry.keys())
            assert entry['TYPE'] in set(['PRICE','TRADE'])
            assert entry['FEEDCODE'] in set(['ESX-FUTURE','SP-FUTURE'])
            timestamp = entry['TIMESTAMP']
            type = entry['TYPE']
            product = entry['FEEDCODE']
            if product not in self._products: self._products[product] = {'PRICES' : [], 'TRADES' : []}
            if type == 'PRICE':
                assert set(['BID_PRICE','BID_VOLUME','ASK_PRICE','ASK_VOLUME']) <= set(entry.keys())
                bid_price = float(entry['BID_PRICE'])
                bid_volume = int(entry['BID_VOLUME'])
                ask_price = float(entry['ASK_PRICE'])
                ask_volume = int(entry['ASK_VOLUME'])
                self._products[product]['PRICES'].append((timestamp, bid_price, bid_volume, ask_price, ask_volume))
            else:
                assert set(['SIDE','PRICE','VOLUME']) <= set(entry.keys())
                side = entry['SIDE']
                price = float(entry['PRICE'])
                volume = int(entry['VOLUME'])
                self._products[product]['TRADES'].append((timestamp,side,price,volume))
    @property
    def products(self):
        self._update_products()
        return self._products

    def start_listen(self, blocking = False):
        print("Listening to the server's data...")
        self.data_queue = multiprocessing.Queue()
        if blocking:
            self._listen_to_server()
        else:
            self.listen_process = multiprocessing.Process(target = self._listen_to_server)
            self.listen_process.start()

    def clear_listen(self):
        sock = self.s
        sock.settimeout(.5)
        while True:
            try:
                sock.recvfrom(1024)
            except:
                break
        sock.settimeout(20)

    def stop_listen(self):
        print("Stopping with listening to the server's data...")
        self.listen_process.terminate()

    def send_order(self, user, feedcode, action,  price, volume):
        text = f"TYPE=ORDER|USERNAME={user}|FEEDCODE={feedcode}|ACTION={action}|PRICE={price}|VOLUME={volume}".encode("ASCII")
        self.s_exchange.sendto(text, (self.UDP_IP, self.UDP_EXCHANGE_PORT))
        if self._should_print:
            print("SENDING:", text)
        try:
            data = self.s_exchange.recvfrom(1024)[0]
        except Exception as e:
            return None
        msg = data.decode("ascii")
        properties = msg.split("|")
        entry = {}
        for p in properties:
            k, v = p.split("=")
            entry[k] = v
        assert entry['TYPE'] == "ORDER_ACK"
        return entry

    def buy(self, user, feedcode, price, volume):
        return self.send_order(user, feedcode, 'BUY', price, volume)

    def sell(self, user, feedcode, price, volume):
        return self.send_order(user, feedcode, 'SELL', price, volume)

if __name__ == "__main__":
    interface = ServerInterface()
    interface.start_listen()
    interface.buy("henk", "SP-FUTURE", 1000, 10000 )
    time.sleep(30)

    interface.stop_listen()
