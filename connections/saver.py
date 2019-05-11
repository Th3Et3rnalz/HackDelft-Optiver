import numpy as np
np.set_printoptions(linewidth=200)
import matplotlib.pyplot as plt
import socket
import multiprocessing
import time
import pickle

UDP_IP = "188.166.115.7"
UDP_BROADCAST_PORT = 7001
UDP_EXCHANGE_PORT = 8001
HELLO_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST".encode("ascii")

def listen_to_server(sock, queue):
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("ascii")
        properties = msg.split("|")
        entry = {}
        for p in properties:
            k,v = p.split("=")
            entry[k] = v
        queue.put(entry)
        # print(entry)


class OptiverInterface:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 8006))
        self.s.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))
        self.listen_process = None
        self.data_queue = None
        self._products = {}
        self.s_exchange = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_exchange.bind(("", 8009))

    def _update_products(self):
        while not self.data_queue.empty():
            entry = self.data_queue.get_nowait()
            assert set(['TYPE','FEEDCODE']) <= set(entry.keys())
            assert entry['TYPE'] in set(['PRICE','TRADE'])
            assert entry['FEEDCODE'] in set(['ESX-FUTURE','SP-FUTURE'])
            type = entry['TYPE']
            product = entry['FEEDCODE']
            if product not in self._products: self._products[product] = {'PRICES' : [], 'TRADES' : []}
            if type == 'PRICE':
                assert set(['BID_PRICE','BID_VOLUME','ASK_PRICE','ASK_VOLUME']) <= set(entry.keys())
                bid_price = float(entry['BID_PRICE'])
                bid_volume = int(entry['BID_VOLUME'])
                ask_price = float(entry['ASK_PRICE'])
                ask_volume = int(entry['ASK_VOLUME'])
                self._products[product]['PRICES'].append((bid_price, bid_volume, ask_price, ask_volume))
            else:
                assert set(['SIDE','PRICE','VOLUME']) <= set(entry.keys())
                side = entry['SIDE']
                price = entry['PRICE']
                volume = entry['VOLUME']
                self._products[product]['TRADES'].append((side, price, volume))

    def get_products(self):
        self._update_products()
        return self._products

    products = property(get_products, None)

    def start_listen(self):
        print("Listening to the server's data...")
        self.data_queue = multiprocessing.Queue()
        self.listen_process = multiprocessing.Process(target = listen_to_server, args = [self.s, self.data_queue])
        self.listen_process.start()

    def stop_listen(self):
        print("Stopping with listening to the server's data...")
        self.listen_process.terminate()

    def plot_product_price(self, product, ax):
        assert product in self.products
        ax.clear()

    def __str__(self):
        return "\n".join(map(str, (self.prices, self.trades)))

    def buy(self, user, feedcode, price, volume):
        text = "TYPE=ORDER|USERNAME={}|FEEDCODE={}|ACTION=BUY|PRICE={}|VOLUME={}".format(user, feedcode, price, volume)
        self.s_exchange.sendto(text, (UDP_IP, UDP_EXCHANGE_PORT))
        end = False
        while not end:
            data = self.s_exchange.recvfrom(1024)[0]
            msg = data.decode("ascii")
            properties = msg.split("|")
            entry = {}
            for p in properties:
                k, v = p.split("=")
                entry[k] = v
            if entry[0] == "ORDER_ACK":
                print(entry)
                end = True

    def sell(self, user, feedcode, price, volume):
        text = "TYPE=ORDER|USERNAME={}|FEEDCODE={}|ACTION=SELL|PRICE={}|VOLUME={}".format(user, feedcode, price, volume).encode("ASCII")
        self.s_exchange.sendto(text, (UDP_IP, UDP_EXCHANGE_PORT))
        end = False
        while not end:
            data = self.s_exchange.recvfrom(1024)[0]
            msg = data.decode("ascii")
            properties = msg.split("|")
            entry = {}
            for p in properties:
                k, v = p.split("=")
                entry[k] = v
            if entry["TYPE"] == "ORDER_ACK":
                print(entry)
                end = True


oi = OptiverInterface()
oi.start_listen()

start = time.time()
end = False
i = 1
while not end:
    try:
        if (time.time() - start) % 600 < 10:
            pickling_on = open("data{}.pickle".format(i), "wb")
            pickle.dump(oi.products, pickling_on)
            pickling_on.close()
            i += 1
            time.sleep(20)
        time.sleep(2)
    except KeyboardInterrupt:
        pickling_on = open("data{}.pickle".format(i), "wb")
        pickle.dump(oi.products, pickling_on)
        pickling_on.close()
        time.sleep(20)
        end = True

oi.stop_listen()
# oi.sell("GROUP25TESTING", "SP-FUTURE", "2950.0", "50")
time.sleep(1)
# print(oi.products)
