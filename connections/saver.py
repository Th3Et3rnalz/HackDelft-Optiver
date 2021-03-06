import matplotlib.pyplot as plt
import matplotlib.dates
import socket
import multiprocessing
import time
import pickle
import datetime
import numpy as np
np.set_printoptions(linewidth=200)

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
        entry['TIMESTAMP'] = datetime.datetime.now()
        queue.put(entry)


def product_monitor():
    plt.show()


class OptiverInterface:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 8003))
        self.s.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))
        self.listen_process = None
        self.product_monitor_processes = {}
        self.product_monitor_figures = []
        self.data_queue = None
        self._products = {}
        self.s_exchange = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_exchange.bind(("", 8006))

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

    def plot_product_price(self, product, ax, options={}):
        assert product in self.products
        ax.clear()
        now = datetime.datetime.now()

        # Get the product prices
        timestamps = list(x[0] for x in self.products[product]['PRICES'])
        bid_prices = list(x[1] for x in self.products[product]['PRICES'])
        ask_prices = list(x[3] for x in self.products[product]['PRICES'])
        timeframe = options.get('timeframe', 60)
        ts, bps, aps = [], [], []
        for t, bp, ap in zip(timestamps, bid_prices, ask_prices):
            if 0 <= (now - t).total_seconds() <= timeframe:
                ts.append(t)
                bps.append(bp)
                aps.append(ap)
        ax.plot(ts, bps, label = 'bid prices', color = 'blue')
        ax.plot(ts, aps, label = 'ask prices', color = 'red')

        # Get the product trades
        timestamps = list(x[0] for x in self.products[product]['TRADES'])
        sides = list(x[1] for x in self.products[product]['TRADES'])
        prices = list(x[2] for x in self.products[product]['TRADES'])
        volumes = list(x[3] for x in self.products[product]['TRADES'])
        ask_ts,ask_ps,ask_vs = [],[],[]
        bid_ts,bid_ps,bid_vs = [],[],[]
        for t,s,p,v in zip(timestamps,sides,prices,volumes):
            if 0 <= (now - t).total_seconds() <= timeframe:
                if s == 'ASK':
                    ask_ts.append(t)
                    ask_ps.append(p)
                    ask_vs.append(v/4)
                else:
                    bid_ts.append(t)
                    bid_ps.append(p)
                    bid_vs.append(v/4)
        ax.scatter(ask_ts, ask_ps, s = ask_vs, label = 'trades', color = 'red')
        ax.scatter(bid_ts, bid_ps, s = bid_vs, label = 'trades', color = 'blue')

        ax.set_title('Product: {}'.format(product))
        ax.set_xlabel('Time')
        ax.set_xlim((now - datetime.timedelta(seconds = timeframe), now))
        ax.xaxis.set_major_locator(matplotlib.dates.SecondLocator())
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y:%M:%S'))
        ax.tick_params(axis = 'x', labelrotation = 90)
        ax.set_ylabel('Price')
        ax.figure.canvas.draw()

    def setup_plot_monitor(self, product, **kwargs):
        print("Starting a monitor of the prices of product {}...".format(product))
        fig = plt.figure()
        ax = fig.gca()
        timer = fig.canvas.new_timer(interval = 500)
        timer.add_callback(self.plot_product_price, product, ax, kwargs)
        timer.start()
        self.product_monitor_figures.append(fig)
        return fig

    def show_plot_monitors(self):
        pmp = multiprocessing.Process(target = product_monitor)
        pmp.start()
        idx = len(self.product_monitor_processes)
        self.product_monitor_processes[idx] = (pmp, self.product_monitor_figures)
        self.product_monitor_figures = []
        return idx

    def close_plot_monitors(self, idx = 0):
        pmp, figs = self.product_monitor_processes[idx]
        pmp.terminate()
        del self.product_monitor_processes[idx]

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


if __name__ == "__main__":
    # Test plotting
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
