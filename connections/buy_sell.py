import socket
import random

UDP_IP = "188.166.115.7"
UDP_BROADCAST_PORT = 7001
UDP_EXCHANGE_PORT = 8001
HELLO_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST".encode("ascii")


class Market:
    def __init__(self):
        self.s_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_receive.bind(("", random.randint(7000, 9000)))
        self.s_receive.sendto(HELLO_MESSAGE, (UDP_IP, UDP_BROADCAST_PORT))

        self.s_exchange = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_exchange.bind(("", random.randint(7000, 9000)))

    def transaction(self, type, user, feedcode, price, volume):
        text = "TYPE=ORDER|USERNAME={}|FEEDCODE={}|ACTION={}|PRICE={}|VOLUME={}".format(user, feedcode, type, price,
                                                                                        volume).encode("ASCII")
        self.s_exchange.sendto(text, (UDP_IP, UDP_EXCHANGE_PORT))

    def buy(self, user, feedcode, price, volume):
        self.transaction("BUY", user, feedcode, price, volume)

    def sell(self, user, feedcode, price, volume):
        self.transaction("SELL", user, feedcode, price, volume)


m = Market()
end = False
value = 10000
while not end:
    m.buy("cookie", "SP-FUTURE", "4000", value)
    data = m.s_exchange.recvfrom(1024)[0]
    msg = data.decode("ascii")
    properties = msg.split("|")
    entry = {}
    for p in properties:
        k, v = p.split("=")
        entry[k] = v
    if entry["TYPE"] == "ORDER_ACK":
        if entry[""]
        print(entry)
        end = True