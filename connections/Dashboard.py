import urllib.request
from aiohttp import web
import socketio
import inspect
import time
import multiprocessing


g = {}
connect_list = []
main_user = ""
start = time.time()
specific_data = []
all_data = []
start_it = 0


def fn(q):
    while True:
        print("Hey there")
        time.sleep(0.2)
        update_it(q)


def update_it(queue):
    global specific_data
    global all_data
    global start_it
    print("this is running")
    try:
        url = 'http://188.166.115.7/data/pnls.csv'
        response = urllib.request.urlopen(url)

        print("We go the data")
        data = response.read()  # a `bytes` object
        text = data.decode('utf-8')

        rows = text.split("\n")
        rows.pop()
        rows.pop()

        data = []

        # for m in
        for i in rows:
            data.append(i.split(";"))

        specific_data = {}
        # print(data)
        for i in data[1:]:
            try:
                # print("pnl: {}, lpnl: {}, type_pnl: {}, type_Lpnl: {}".format(i[1], i[2], type(i[1]), type(i[2])))
                exposure = int(float(i[1]) - float(i[2]))
            except:
                exposure = "NaN"
            specific_data[i[0]] = {'username': i[0], 'pnl': i[1], 'lpnl': i[2], 'volume': i[3],
                                   'esx': i[4], 'sp': i[5], 'time': time.time() - start, 'exposure': exposure}
        # print(specific_data)
        queue.put(specific_data)

    except TimeoutError:
        print("ERROR, SH*T NOT WORKING, AGAIN...")


q = multiprocessing.Queue()
p = multiprocessing.Process(target=fn, args=[q])
p.start()

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)


async def index(request):
    if inspect.isclass(request) is not True:
        with open('main.html') as f:
            return web.Response(text=f.read(), content_type='text/html')


@sio.on('demand')
async def print_message(sid, message):
    delta_t = start - time.time()
    if message == "I demand your data":
        print("Socket ID: ", sid)
        while not q.empty():
            all_data.append(q.get())
            print(len(all_data))
        await sio.emit('data', all_data)


@sio.on('connect')
async def connect(sid, environ):
    global main_user
    print("\nNEW CONNECTION:")
    print('ID:      ', sid)
    print('Browser: ', environ['HTTP_USER_AGENT'])
    print('IP:      ', environ['REMOTE_ADDR'], end="\n\n")
    connect_list.append(sid)
    if True:
        await sio.emit('first_connect', sid)
    if len(connect_list) == 1:
        main_user = sid
        await sio.emit('set_main_user', main_user)
    g['q'] = len(connect_list)


@sio.on('disconnect')
async def disconnect(sid):
    global main_user
    print('DISCONNECT: ', sid)
    connect_list.remove(sid)
    g['q'] = len(connect_list)
    if sid == main_user and len(connect_list) > 0:
        main_user = connect_list[0]
        print("NEW MAIN USER: ", main_user)
        await sio.emit('set_main_user', main_user)

app.router.add_get('/', index)
app.router.add_static('/static/', path="static", name='static')


if __name__ == '__main__':
    print("running")
    web.run_app(app)
