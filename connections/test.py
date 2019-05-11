import socket

UDP_IP = "188.166.115.7"
UDP_PORT = 7001
MESSAGE = "TYPE=SUBSCRIPTION_REQUEST".encode("ascii")

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 8000))
    s.sendto(MESSAGE, (UDP_IP, UDP_PORT))
    while True:
        data, addr = s.recvfrom(1024)
        print("Received message:", data)
