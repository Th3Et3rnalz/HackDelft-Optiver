import socket
import multiprocessing
import time

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
        self.s.bind(("",8000))
        self.s.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))
        self.listen_process = None
        self.data_queue = None
        self._prices = []
        self._trades = []

    def _update_prices_trades(self):
        while not self.data_queue.empty():
            entry = self.data_queue.get_nowait()
            assert entry['TYPE'] in set(['PRICE','TRADE'])
            if entry['TYPE'] == 'PRICE':
                self._prices.append(entry)
            else:
                self._trades.append(entry)

    def get_prices(self):
        self._update_prices_trades()
        return self._prices

    prices = property(get_prices, None)

    def get_trades(self):
        self._update_prices_trades()
        return self._trades

    trades = property(get_trades, None)

    def start_listen(self):
        print("Listening to the server's data...")
        self.data_queue = multiprocessing.Queue()
        self.listen_process = multiprocessing.Process(target = listen_to_server, args = [self.s, self.data_queue])
        self.listen_process.start()

    def stop_listen(self):
        print("Stopping with listening to the server's data...")
        self.listen_process.terminate()

    def __str__(self):
        return "\n".join(map(str, (self.prices, self.trades)))

oi = OptiverInterface()
oi.start_listen()
time.sleep(5)
oi.stop_listen()
time.sleep(1)
print(oi.prices)
print(oi.trades)
