import urllib.request
rom aiohttp import web
import socketio
import inspect
import time
from threading import Timer
import random


url = 'http://188.166.115.7/data/pnls.csv'
response = urllib.request.urlopen(url)
print("We go the data")
data = response.read()      # a `bytes` object
text = data.decode('utf-8')

rows = text.split("\n")
rows.pop()
rows.pop()

data = []
# for m in
for i in rows:
    data.append(i.split(";"))

user = "cookie3"
specific_data = []
try:
    for i in data:
        ct = i.count(user)
        if ct != 0:
            specific_data = {'username': i[0], 'Total PnL': i[1], 'Total locked PnL': i[2], 'Traded volume': i[3],
                            'ESX position': i[4], 'SP position': i[5]}
            break
except:
    pass

print(specific_data)