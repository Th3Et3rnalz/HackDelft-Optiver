from server_interface import ServerInterface
from multiprocessing import Process, Manager
import numpy as np
import time

class Trader:
    def __init__(self, name, callback=None):
        self._name = name
        self._server = ServerInterface()
        self._order_procs = []
        self.order_N = 0

        self._proc_manager = Manager()
        self._proc_return_dict = self._proc_manager.dict()

        self.cash = 0

        if callback is None:
            self._callback = lambda trader, entry: None
        else:
            self._callback = callback

        self._positions = {
            "SP-FUTURE":0,
            "ESX-FUTURE":0
        }

    def buy(self, feedcode, amount):
        def fn(server, name, feedcode, amount, return_dict, order_N):
            return_dict[order_N] = server.buy(name, feedcode, 10000, np.ceil(amount).astype(int))
        proc =  Process(target=fn, args = (self._server, self._name, feedcode, amount, self._proc_return_dict, self.order_N))
        print(self.order_N, "BUY", feedcode, amount)
        self._order_procs.append((self.order_N, proc));
        self.order_N += 1
        proc.start()

    def sell(self, feedcode, amount):
        def fn(server, name, feedcode, amount, return_dict, order_N):
            return_dict[order_N] = server.sell(name, feedcode, 10, np.ceil(amount).astype(int))
        proc =  Process(target=fn, args = (self._server, self._name, feedcode, amount, self._proc_return_dict, self.order_N))
        print(self.order_N, "SELL", feedcode, amount)
        self._order_procs.append((self.order_N, proc));
        self.order_N += 1
        proc.start()



    def _process_orders(self):
        del_orders = []
        for i in range(len(self._order_procs)):
            order_N, proc = self._order_procs[i]
            if not proc.is_alive():
                proc.join()
                ret = self._proc_return_dict[order_N]
                del_orders.append(i)
                if ret is None:
                    print(order_N, "NOT ACK")
                elif int(ret['TRADED_VOLUME']) == 0:
                    print(order_N, "NO TRADE")
                else:
                    print(order_N, "ACK", ret['FEEDCODE'], ret['PRICE'], ret['TRADED_VOLUME'])

                    self.cash += -1*float(ret['PRICE'])*int(ret['TRADED_VOLUME'])
                    print( "CASH", self.cash)
                    if ret['FEEDCODE'] not in self._positions:
                        self._positions[ret['FEEDCODE']] = 0
                    self._positions[ret['FEEDCODE']] += int(ret['TRADED_VOLUME'])
        for i in del_orders[::-1]:
            del self._order_procs[i]

    def callback(self, entry):
        self._process_orders()
        self._callback(self, entry)


    def reset_positions(self):
        done = False
        while len(self._order_procs) != 0:
            time.sleep(1)
            self._process_orders()
        while not done:
            done = True
            for feedcode, value in self._positions.items():
                if value < 0:
                    self.buy(feedcode, min(-value,300))
                    done = False
                elif value>0:
                    self.sell(feedcode, min(value,300))
                    done = False
            while len(self._order_procs) != 0:
                time.sleep(1)
                self._process_orders()
        print("--------------- DONE RESETTING -------------")
        print( "CASH", self.cash)
        print("--------------------------------------------")
        self._server.clear_listen()




    def start_trading(self):
        self._server.register_callback(self.callback)
        self._server.start_listen(blocking=True)


if __name__ == "__main__":
    import time
    trader = Trader("test25")
    trader.buy('SP-FUTURE', 100)
    trader.callback(None)
    trader.buy('SP-FUTURE', 100)
    trader.callback(None)
    trader.buy('SP-FUTURE', 100)
    trader.callback(None)
    trader.buy('ESX-FUTURE', 1000)
    trader.callback(None)
    time.sleep(2)
    trader.callback(None)
    print(trader._positions)
    trader.reset_positions()
    time.sleep(2)
    trader.callback(None)
    print(trader._positions)
