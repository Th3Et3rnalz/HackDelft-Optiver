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
        queue.put(msg)
        print("The following message was received from the server:", msg)

class OptiverInterface:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("",8000))
        self.s.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))
        self.listen_process = None
        self.data_queue = None
        self._msgs = []

    msgs = @property(get_msgs, None)

    def get_msgs(self):
        for msg in iter(self.data_queue.get, None):
            pass

    def start_listen(self):
        self.data_queue = multiprocessing.Queue()
        self.listen_process = multiprocessing.Process(target = listen_to_server, args = [self.s, self.listen_queue])
        self.listen_process.start()

    def stop_listen(self):
        self.listen_process.terminate()

    def __str__(self):
        return "\n".join(map(str, (self.prices, self.trades)))

oi = OptiverInterface()
oi.start_listen()
time.sleep(5)
oi.stop_listen()
