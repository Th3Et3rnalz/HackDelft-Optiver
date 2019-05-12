import numpy as np
np.set_printoptions(linewidth=200)
import matplotlib.pyplot as plt
import matplotlib.dates
import socket
import multiprocessing
import time
import pickle
import datetime

UDP_IP = "188.166.115.7"
UDP_BROADCAST_PORT = 7001
UDP_EXCHANGE_PORT = 8001
HELLO_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST".encode("ascii")

percentage_bought_threshold = 0.7
risk_factor = 0.2

class Trader:
    def __init__(self, name):
        self.name = name
        self.position = {}
        self.cash = 0
        self.stashed_trades = {}
        self.acknowledgements = multiprocessing.Queue()
        self.oi = OptiverInterface()
        self.oi.append_callback(self.handle_stash)
        self.oi.append_callback(self.perform_trade)
        self.oi.setup_plot_monitor(['SP-FUTURE','ESX-FUTURE'], timeframe = 10)
        self.oi.show_plot_monitors()
        self.oi.listen()

    def stash_buy(self, product, price, volume):
        self.stashed_trades[product] = ('BUY', price, volume)

    def stash_sell(self, product, price, volume):
        self.stashed_trades[product] = ('SELL', price, volume)

    def handle_stash(self, entry):
        if entry['TYPE'] == 'TRADE':
            product = entry['FEEDCODE']
            other_product = 'ESX-FUTURE' if product == 'SP-FUTURE' else 'SP-FUTURE'
            if other_product in self.stashed_trades and self.stashed_trades[other_product] is not None:
                action, price, volume = self.stashed_trades[other_product]
                if action == 'BUY':
                    self.place_buy(other_product, price, volume)
                else:
                    self.place_sell(other_product, price, volume)
                self.stashed_trades[other_product] = None

    def place_buy(self, product, price, volume):
        print("[{}] {} PLACED. PRODUCT: {}. PRICE: {}. VOLUME: {}.".format(datetime.datetime.now(), 'BUY', product, price, volume))
        p = multiprocessing.Process(target = self.oi.buy, args = [self.name, product, price, volume, self.acknowledgements])
        p.start()

    def place_sell(self, product, price, volume):
        print("[{}] {} PLACED. PRODUCT: {}. PRICE: {}. VOLUME: {}.".format(datetime.datetime.now(), 'SELL', product, price, volume))
        p = multiprocessing.Process(target = self.oi.sell, args = [self.name, product, price, volume, self.acknowledgements])
        p.start()

    def synchronize(self):
        while not self.acknowledgements.empty():
            ack = self.acknowledgements.get_nowait()
            ack['TIMESTAMP'] = datetime.datetime.now()
            if int(ack['VOLUME']) > 0:
                print("[{}] {} ACKNOWLEDGED. PRODUCT: {}. PRICE: {}. VOLUME: {}.".format(ack['TIMESTAMP'], ack['ACTION'], ack['FEEDCODE'], ack['PRICE'], ack['VOLUME']))
                self.oi.data_queue.put(ack)
                if ack['ACTION'] == 'BUY':
                    self.cash -= float(ack['PRICE']) * ack['VOLUME']
                    if ack['FEEDCODE'][6:] not in self.position: self.position[ack['FEEDCODE'][6:]] = ack['VOLUME']
                    else: self.position[ack['FEEDCODE'][6:]] += ack['VOLUME']
                else:
                    self.cash += float(ack['PRICE']) * ack['VOLUME']
                    if ack['FEEDCODE'][6:] not in self.position: self.position[ack['FEEDCODE'][6:]] = -ack['VOLUME']
                    else: self.position[ack['FEEDCODE'][6:]] -= ack['VOLUME']
            else:
                print("[{}] {} REJECTED. PRODUCT: {}.".format(ack['TIMESTAMP'], ack['ACTION'], ack['FEEDCODE']))
            print(self)

    def __str__(self):
        ss = []
        ss.append('Cash: ${}.'.format(self.cash))
        for product,position in self.position.items():
            ss.append('Position {}: {}.'.format(product,position))
        ss.append('Total: ${}.'.format(self.cash + sum(position * self.oi.get_time_price(product)[0] for product,position in self.position.items())))
        return '  ' + '\n  '.join(ss)

    def perform_trade(self, entry):
        self.synchronize()
        if entry['TYPE'] == 'PRICE':

            # Get the relevant information on which to base the decision
            product,(t,s,p,v) = self.oi.get_last_trade()
            other_product = 'ESX-FUTURE' if product == 'SP-FUTURE' else 'SP-FUTURE'
            bp,bv,ap,av = self.oi.get_time_price(product, (t - datetime.timedelta(milliseconds = 1)))
            obp,obv,oap,oav = self.oi.get_time_price(other_product, (t - datetime.timedelta(milliseconds = 1)))
            nbp,nbv,nap,nav = self.oi.get_time_price(other_product, datetime.datetime.now())

            if s == 'BID':
                # print("Received bid.")
                percentage_bought = v / bv
                percentage_bought_factor = 0
                if percentage_bought > percentage_bought_threshold:
                    percentage_bought_factor = percentage_bought_factor = (percentage_bought - percentage_bought_threshold)/(1. - percentage_bought_threshold)
                trade_volume_factor = v / 500

                price_difference = nap - oap
                price_difference_factor = 0
                if price_difference < - 0.5:
                    price_difference_factor = -price_difference

                amount = np.ceil(risk_factor * nav * percentage_bought_factor * trade_volume_factor * price_difference_factor / 4).astype(int)
                if amount > 0:
                    self.stash_buy(other_product, nap, amount)

            else:
                # print("Received ask.")

                # Received trade is ASK so SELL
                percentage_bought = v / av
                percentage_bought_factor = 0.
                if percentage_bought > percentage_bought_threshold:
                    percentage_bought_factor = (percentage_bought - percentage_bought_threshold)/(1. - percentage_bought_threshold)
                trade_volume_factor = v / 500

                price_difference = nap - oap
                price_difference_factor = 0
                if price_difference > 0.5:
                    price_difference_factor = price_difference

                amount = np.ceil(risk_factor * nbv * percentage_bought_factor * trade_volume_factor * price_difference_factor / 4).astype(int)

                if amount > 0:
                    self.stash_sell(other_product, nbp, amount)

def product_monitor():
    plt.show()

class OptiverInterface:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 8005))
        self.s.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))
        self.product_monitor_processes = {}
        self.product_monitor_figures = []
        self.data_queue = multiprocessing.Queue()
        self.products = {}
        self.s_exchange = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_exchange.bind(("", 8002))
        self.callbacks = []

    def synchronize(self):
        while not self.data_queue.empty():
            entry = self.data_queue.get_nowait()
            # if entry['FEEDCODE'] not in set(['ESX-FUTURE', 'SP-FUTURE']):
            #     print(entry['FEEDCODE'])
            self._update_products(entry)

    def append_callback(self, c):
        self.callbacks.append(c)

    def _update_products(self, entry):
        assert set(['TYPE','FEEDCODE','TIMESTAMP']) <= set(entry.keys())
        assert entry['TYPE'] in set(['PRICE','TRADE'])
        # assert entry['FEEDCODE'] in set(['ESX-FUTURE','SP-FUTURE'])
        timestamp = entry['TIMESTAMP']
        type = entry['TYPE']
        product = entry['FEEDCODE']
        if product not in self.products: self.products[product] = {'PRICES' : [], 'TRADES' : []}
        if type == 'PRICE':
            assert set(['BID_PRICE','BID_VOLUME','ASK_PRICE','ASK_VOLUME']) <= set(entry.keys())
            bid_price = float(entry['BID_PRICE'])
            bid_volume = int(entry['BID_VOLUME'])
            ask_price = float(entry['ASK_PRICE'])
            ask_volume = int(entry['ASK_VOLUME'])
            self.products[product]['PRICES'].append((timestamp, bid_price, bid_volume, ask_price, ask_volume))
        else:
            assert set(['SIDE','PRICE','VOLUME']) <= set(entry.keys())
            side = entry['SIDE']
            price = float(entry['PRICE'])
            volume = int(entry['VOLUME'])
            self.products[product]['TRADES'].append((timestamp,side,price,volume))

    def listen(self):
        while True:
            data, addr = self.s.recvfrom(1024)
            msg = data.decode("ascii")
            properties = msg.split("|")
            entry = {}
            for p in properties:
                k,v = p.split("=")
                entry[k] = v
            now = datetime.datetime.now()
            print('[{}] {}'.format(now, entry))
            entry['TIMESTAMP'] = now
            self._update_products(entry)
            self.data_queue.put(entry)
            for c in self.callbacks:
                c(entry)

    def get_last_trade(self):
        return max(((product,x['TRADES'][-1]) for product,x in self.products.items() if len(x['TRADES']) > 0), key = lambda x : x[1][0])

    def get_timeframe(self, product, now = None, timeframe = 60):
        if now is None: now = datetime.datetime.now()
        data = self.products[product]
        new_data = {'PRICES' : [], 'TRADES' : []}
        for t,bp,bv,ap,av in data['PRICES']:
            if 0 <= (now - t).total_seconds() <= timeframe:
                new_data['PRICES'].append((t,bp,bv,ap,av))
        new_data['PRICES'].sort(key = lambda x : x[0])
        for t,s,p,v in data['TRADES']:
            if 0 <= (now - t).total_seconds() <= timeframe:
                new_data['TRADES'].append((t,s,p,v))
        new_data['TRADES'].sort(key = lambda x : x[0])
        return new_data

    def get_time_price(self, product, time = None):
        # assert product in self.products
        if product not in self.products:
            print("WARNING: Product {} not in the products.".format(product))
            return
        if time is None: time = datetime.datetime.now()
        if len(self.products[product]['PRICES']) == 0 or time <= self.products[product]['PRICES'][0][0]:
            return (1e8,1e8,1e8,1e8)
        for t,bp,bv,ap,av in reversed(self.products[product]['PRICES']):
            if t <= time:
                return (bp,bv,ap,av)

    def plot_product_price(self, product, ax, options = {}):
        # assert product in self.products
        self.synchronize()
        if product not in self.products:
            print("WARNING: Product {} not in the products.".format(product))
            return
        if options.get('clear',True): ax.clear()

        # Get the data
        now = options.get('now', datetime.datetime.now())
        timeframe = options.get('timeframe', 60)
        data = self.get_timeframe(product, now = now, timeframe = timeframe)

        # Get the product prices
        ts = list(x[0] for x in self.products[product]['PRICES'])
        bps = list(x[1] for x in self.products[product]['PRICES'])
        aps = list(x[3] for x in self.products[product]['PRICES'])
        ax.step(ts, bps, where = 'post', label = 'bid prices', color = options.get('bid color', 'blue'))
        ax.step(ts, aps, where = 'post', label = 'ask prices', color = options.get('ask color', 'red'))

        # Get the product trades
        timestamps = list(x[0] for x in data['TRADES'])
        sides = list(x[1] for x in data['TRADES'])
        prices = list(x[2] for x in data['TRADES'])
        volumes = list(x[3] for x in data['TRADES'])
        ask_ts,ask_ps,ask_vs = [],[],[]
        bid_ts,bid_ps,bid_vs = [],[],[]
        for t,s,p,v in zip(timestamps,sides,prices,volumes):
            if s == 'ASK':
                ask_ts.append(t)
                ask_ps.append(p)
                ask_vs.append(v/4)
            else:
                bid_ts.append(t)
                bid_ps.append(p)
                bid_vs.append(v/4)
        ax.scatter(ask_ts, ask_ps, s = ask_vs, label = 'ask trades', color = options.get('ask color', 'red'))
        ax.scatter(bid_ts, bid_ps, s = bid_vs, label = 'bid trades', color = options.get('bid color', 'blue'))

        for t,p,v in zip(ask_ts,ask_ps,ask_vs):
            ax.text(t, p, str(v), va = 'baseline', ha = 'center')
        for t,p,v in zip(bid_ts,bid_ps,bid_vs):
            ax.text(t, p, str(v), va = 'baseline', ha = 'center')

        self.set_default_figure_layout(now, timeframe, ax)
        ax.set_title('Product: {}'.format(product))
        ax.set_ylabel('Price')

        if options.get('draw', True): ax.figure.canvas.draw()

    def plot_product_volume(self, product, ax, options = {}):
        # assert product in self.products
        self.synchronize()
        if product not in self.products:
            print("WARNING: Product {} not in the products.".format(product))
            return
        if options.get('clear',True): ax.clear()

        # Get the data
        now = options.get('now', datetime.datetime.now())
        timeframe = options.get('timeframe', 60)
        data = self.get_timeframe(product, now = now, timeframe = timeframe)

        # Get the product volumes
        ts = list(x[0] for x in data['TRADES'])
        ss = list(x[1] for x in data['TRADES'])
        vs = list(x[3] for x in data['TRADES'])

        ask_ts,ask_vs,bid_ts,bid_vs = [],[],[],[]

        for t,s,v in zip(ts,ss,vs):
            bp,bv,ap,av = self.get_time_price(product, t - datetime.timedelta(milliseconds = 1))
            if s == 'ASK':
                ask_ts.append(t)
                ask_vs.append(v/av)
            else:
                bid_ts.append(t)
                bid_vs.append(v/bv)
        ax.scatter(ask_ts, ask_vs, label = 'ask volumes', color = 'red', marker = options.get('marker','o'))
        ax.scatter(bid_ts, bid_vs, label = 'bid volumes', color = 'blue', marker = options.get('marker','o'))

        self.set_default_figure_layout(now, timeframe, ax)
        ax.set_title('Volumes')
        ax.set_ylabel('Volume')
        ax.set_ylim((0,1))

        if options.get('draw', True): ax.figure.canvas.draw()

    def setup_plot_monitor(self, products, **kwargs):
        fig = plt.figure()
        timer = fig.canvas.new_timer(interval = 500)
        kwargs['draw'] = False
        vol_kwargs = kwargs.copy()
        trade_kwargs = kwargs.copy()
        trade_kwargs['clear'] = False
        trade_kwargs['ask color'] = 'cyan'
        trade_kwargs['bid color'] = 'magenta'
        vol_ax = fig.add_subplot(3,1,3)
        for i,product in enumerate(products):
            print("Starting a monitor of the prices of product {}...".format(product))
            ax = fig.add_subplot(3,1,i+1)
            timer.add_callback(self.plot_product_price, product, ax, kwargs.copy())
            timer.add_callback(self.plot_product_price, 'TRADE_' + product, ax, trade_kwargs.copy())
            if i == len(products) - 1: vol_kwargs['draw'] = True
            timer.add_callback(self.plot_product_volume, product, vol_ax, vol_kwargs.copy())
            vol_kwargs['clear'] = False
            vol_kwargs['marker'] = 'x'
        timer.start()
        self.product_monitor_figures.append(fig)
        return fig

    def set_default_figure_layout(self, now, timeframe, ax):
        ax.set_xlabel('Time')
        ax.set_xlim((now - datetime.timedelta(seconds = timeframe), now))
        ax.xaxis.set_major_locator(matplotlib.dates.SecondLocator())
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y:%M:%S'))
        ax.tick_params(axis = 'x', labelrotation = 90)

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

    def buy(self, user, feedcode, price, volume, queue = None):
        text = "TYPE=ORDER|USERNAME={}|FEEDCODE={}|ACTION=BUY|PRICE={}|VOLUME={}".format(user, feedcode, price, volume)
        # print("----------------")
        # print(text)
        # print("----------------")
        # time.sleep(.1 * sleep)
        self.s_exchange.sendto(text.encode('ascii'), (UDP_IP, UDP_EXCHANGE_PORT))
        data = self.s_exchange.recvfrom(1024)[0]
        msg = data.decode("ascii")
        properties = msg.split("|")
        entry = {}
        for p in properties:
            k, v = p.split("=")
            entry[k] = v
        assert entry['TYPE'] == "ORDER_ACK"
        entry['TYPE'] = 'TRADE'
        entry['FEEDCODE'] = 'TRADE_' + entry['FEEDCODE']
        entry['VOLUME'] = int(entry['TRADED_VOLUME'])
        entry['SIDE'] = 'ASK'
        entry['ACTION'] = 'BUY'
        if queue is None:
            return entry
        else:
            queue.put(entry)

    def sell(self, user, feedcode, price, volume, queue = None):
        text = "TYPE=ORDER|USERNAME={}|FEEDCODE={}|ACTION=SELL|PRICE={}|VOLUME={}".format(user, feedcode, price, volume)
        # print("----------------")
        # print(text)
        # print("----------------")
        # time.sleep(sleep * .1)
        self.s_exchange.sendto(text.encode('ascii'), (UDP_IP, UDP_EXCHANGE_PORT))
        data = self.s_exchange.recvfrom(1024)[0]
        msg = data.decode("ascii")
        properties = msg.split("|")
        entry = {}
        for p in properties:
            k, v = p.split("=")
            entry[k] = v
        assert entry['TYPE'] == "ORDER_ACK"
        entry['TYPE'] = 'TRADE'
        entry['FEEDCODE'] = 'TRADE_' + entry['FEEDCODE']
        entry['VOLUME'] = -int(entry['TRADED_VOLUME'])
        entry['SIDE'] = 'BID'
        entry['ACTION'] = 'SELL'
        if queue is None:
            return entry
        else:
            queue.put(entry)

if __name__ == "__main__":
    # Test plotting
    trader = Trader(name = 'hendrik-ido-ambacht-3')
