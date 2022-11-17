#!/usr/bin/env python

import socket
import zeroconf
import asyncio
import websockets
import time
import json
import traceback
import sys
import signal
import spooler
import async_prompt
from tty_colors import COL

HOSTNAME='plotter-server'
PORT=4321
PING_INTERVAL=10
PING_TIMEOUT=5

prompt = None
zc = None
num_clients = 0
clients = []

def status_str(status):
    match status['status']:
        case 'waiting':
            return(f'{COL.BOLD}Waiting for jobs{COL.OFF}')
        case 'confirm_plot':
            return(f'{COL.BOLD}{COL.YELLOW}Confirm to plot [{status["job"]}]{COL.OFF}')
        case 'plotting':
            return(f'{COL.BOLD}{COL.GREEN}Plotting [{status["job"]}]{COL.OFF}')

def col_num(n):
    if n > 0:
        return f'{COL.BOLD}{COL.GREEN}{n}{COL.OFF}'
    else:
        return f'{COL.BOLD}{n}{COL.OFF}'

def print_status():
    s = spooler.status()
    print(f'  Jobs: {col_num(s["queue_size"])}  |  Clients: {col_num(len(clients))}  |  Status: {status_str(s)}\n')

def setup_prompt():
    global prompt
    global print
    prompt = async_prompt.AsyncPrompt()
    print = prompt.print # replace global print function

def remove_prompt():
    global prompt
    del prompt # force destructor, causes terminal to restore

def disable_sigint():
    signal.signal(signal.SIGINT, lambda *args: None) 

def add_zeroconf_service():
    global zc
    print('Registering zeroconf service...')
    lanip = socket.gethostbyname(socket.gethostname())
    service_info = zeroconf.ServiceInfo(
        "_ws._tcp.local.",
        f'{HOSTNAME}._ws._tcp.local.',
        addresses=[lanip],
        port=PORT,
        server=f"{HOSTNAME}.local."
    )
    zc = zeroconf.Zeroconf()
    zc.register_service(service_info)
    print(f'Registered: {HOSTNAME}.local -> {lanip} (Port {PORT})')

def remove_zeroconf_service():
    if zc != None: 
        print('Unregistering zeroconf service...')
        zc.unregister_all_services()

async def send_msg(msg, ws):
    if type(msg) is dict: msg = json.dumps(msg)
    try:
        await ws.send(msg)
    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
        pass

async def on_queue_size(size):
    cbs = []
    for ws in clients:
        cbs.append( send_msg({'type': 'queue_length', 'length': size}, ws) )
    await asyncio.gather(*cbs)

async def send_current_queue_size(ws):
    await send_msg( {'type': 'queue_length', 'length': spooler.queue_size()}, ws )

async def handle_message(message, ws):
    async def on_queue_position(pos, job):
        await send_msg( {'type': 'queue_position', 'position': pos, 'id': job['id']}, ws )
    async def on_done(job):
        await send_msg( {'type': 'job_done', 'id': job['id']}, ws )
    async def on_cancel(job):
        await send_msg( {'type': 'job_canceled', 'id': job['id']}, ws )
    async def on_error(msg, job):
        await send_msg( {'type': 'error', 'msg': msg, 'id': job['id']}, ws )
    msg = json.loads(message)
    if msg['type'] == 'echo':
        await ws.send(message)
    elif msg['type'] == 'plot':
        qsize = spooler.queue_size()
        result = await spooler.enqueue(msg, on_queue_position, on_done, on_cancel, on_error)
        if result and qsize > 0: print_status() # Don't print status if queue is empty -> Status will be printed by spooler
    elif msg['type'] == 'cancel':
        result = await spooler.cancel(msg['client'])
        if result: print_status()

async def handle_connection(ws):
    global num_clients
    num_clients += 1
    clients.append(ws)
    remote_address = ws.remote_address # store remote address (might not be available on disconnect)
    print(f'({num_clients}) Connected:    {remote_address[0]}:{remote_address[1]}')
    print_status()
    await send_current_queue_size(ws)
    try:
        # The iterator exits normally when the connection is closed with close code 1000 (OK) or 1001 (going away). It raises a ConnectionClosedError when the connection is closed with any other code.
        async for message in ws:
            # print(f'Message ({ws.remote_address[0]}:{ws.remote_address[1]}):', message)
            await handle_message(message, ws)
    except websockets.exceptions.ConnectionClosedError:
        pass
    num_clients -= 1
    clients.remove(ws)
    print(f'({num_clients}) Disconnected: {remote_address[0]}:{remote_address[1]} ({ws.close_code}{(" " + ws.close_reason).rstrip()})')
    print_status()

async def main():
    setup_prompt() # needs to be called within event loop
    async with websockets.serve(handle_connection, "0.0.0.0", PORT, ping_interval=PING_INTERVAL, ping_timeout=PING_TIMEOUT):
        print("Server running...")
        spooler.set_queue_size_cb(on_queue_size)
        # await asyncio.Future() # run forever
        await spooler.start(prompt, print_status) # run forever

def quit():
    print('Quitting...')
    remove_prompt()
    remove_zeroconf_service()

if __name__ == '__main__':
    try:
        add_zeroconf_service()
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except:
        traceback.print_exception( sys.exception() )
    finally:
        disable_sigint() # prevent another Control-C
        quit()