USE_ZEROCONF      = 0
ZEROCONF_HOSTNAME = 'plotter'

USE_PORKBUN         = 0
PORKBUN_ROOT_DOMAIN = 'process.tools'
PORKBUN_SUBDOMAIN   = 'plotter-local'
PORKBUN_TTL         = 600
PORKBUN_SSL_OUTFILE = 'cert/process.tools.pem'

BIND_IP  = '0.0.0.0'
PORT     = 0 # Use 0 for default ports (80 for http, 443 for ssl/tls)
USE_SSL  = 1
# SSL_CERT = 'cert/localhost.pem' # Certificate file in pem format (can contain private key as well)
# SSL_KEY  = None # Private key file in pem format (If None, the key needs to be contained in SSL_CERT)
SSL_CERT = 'cert/process.tools.pem'
SSL_KEY  = None

PING_INTERVAL = 10
PING_TIMEOUT  = 5
SHOW_CONNECTION_EVENTS = 1 # Print when clients connect/disconnect
MAX_MESSAGE_SIZE_MB = 5 # in MB (Default in websockets lib is 2)

QUEUE_HEADERS = ['#', 'Client', 'Hash', 'Lines', 'Layers', 'Travel', 'Ink', 'Format', 'Speed', 'Duration']


import textual
from textual import on
from textual.events import Key
from textual.app import App as TextualApp
from textual.widgets import Button, DataTable, RichLog, Footer, Header, Static, ProgressBar, Rule
from textual.containers import Horizontal, Vertical
from hotkey_button import HotkeyButton

import asyncio
import websockets
import spooler
import json
import math
import subprocess
import porkbun


app = None
ssl_context = None
num_clients = 0
clients = []


# Status simply shows up in the header
def print_status():
    app.update_header()

def setup_ssl():
    import ssl
    import os.path
    
    if USE_SSL:
        global ssl_context
        try:
            cert_file = os.path.join( os.path.dirname(__file__), SSL_CERT )
            key_file = None if SSL_KEY == None else os.path.join( os.path.dirname(__file__), SSL_KEY )
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_file, key_file)
            print(f'TLS enabled with certificate: {SSL_CERT}{"" if SSL_KEY == None else " + " + SSL_KEY}')
        except FileNotFoundError:
            print(f'Certificate not found, TLS disabled')
            ssl_context = None
        except:
            print(f'Error establishing TLS context, TLS disabled')
            ssl_context = None
    global PORT
    if PORT == 0: PORT = 80 if ssl_context == None else 443

async def handle_connection(ws):
    global num_clients
    num_clients += 1
    clients.append(ws)
    remote_address = ws.remote_address # store remote address (might not be available on disconnect)
    if SHOW_CONNECTION_EVENTS:
        print(f'({num_clients}) Connected:    {remote_address[0]}:{remote_address[1]}')
        print_status()
    # await send_current_queue_size(ws)
    try:
        # The iterator exits normally when the connection is closed with close code 1000 (OK) or 1001 (going away). It raises a ConnectionClosedError when the connection is closed with any other code.
        async for message in ws:
            # print(f'Message ({ws.remote_address[0]}:{ws.remote_address[1]}):', message)
            await handle_message(message, ws)
    except websockets.exceptions.ConnectionClosedError:
        pass
    num_clients -= 1
    clients.remove(ws)
    if SHOW_CONNECTION_EVENTS:
        print(f'({num_clients}) Disconnected: {remote_address[0]}:{remote_address[1]} ({ws.close_code}{(" " + ws.close_reason).rstrip()})')
        print_status()

async def send_msg(msg, ws):
    if type(msg) is dict: msg = json.dumps(msg)
    try:
        await ws.send(msg)
    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
        pass
        
async def on_queue_size(size):
    app.update_job_queue()
    app.update_header()
    cbs = []
    for ws in clients:
        cbs.append( send_msg({'type': 'queue_length', 'length': size}, ws) )
    await asyncio.gather(*cbs)

async def send_current_queue_size(ws):
    await send_msg( {'type': 'queue_length', 'length': spooler.num_jobs()}, ws )

async def handle_message(message, ws):
    async def on_queue_position(pos, job):
        await send_msg( {'type': 'queue_position', 'position': pos}, ws )
    async def on_done(job):
        await send_msg( {'type': 'job_done'}, ws )
    async def on_cancel(job):
        await send_msg( {'type': 'job_canceled'}, ws )
    async def on_error(msg, job):
        await send_msg( {'type': 'error', 'msg': msg}, ws )
    
    try:
        msg = json.loads(message)
    except JSONDecodeError:
        return
    
    if msg['type'] == 'echo':
        await ws.send(message)
    elif msg['type'] == 'plot':
        qsize = spooler.num_jobs()
        result = await spooler.enqueue(msg, on_queue_position, on_done, on_cancel, on_error)
        if result and qsize > 0: print_status() # Don't print status if queue is empty -> Status will be printed by spooler
    elif msg['type'] == 'cancel':
        result = await spooler.cancel(msg['client'])
        if result: print_status()

async def run_server(app):
    async with websockets.serve(handle_connection, BIND_IP, PORT, ping_interval=PING_INTERVAL, ping_timeout=PING_TIMEOUT, ssl=ssl_context, max_size=MAX_MESSAGE_SIZE_MB*(2**20)):
        print(f'Server running on {"ws" if ssl_context == None else "wss"}://{BIND_IP}:{PORT}')
        print()
        spooler.set_queue_size_cb(on_queue_size)
        # await asyncio.Future() # run forever
        await spooler.start(app) # run forever


class App(TextualApp):
    prompt_future = None
    
    def compose(self):
        global header, queue, log, footer
        header = Header(icon = '🖨️', show_clock = True, time_format = '%H:%M')
        queue = DataTable(id = 'queue')
        log = RichLog(markup=True)
        footer = Footer(id="footer", show_command_palette=True)
        
        global job_current, job_status,job_progress
        job_current = DataTable()
        job_status = Static("Status: Waiting")
        job_progress = ProgressBar()
        
        global col_left, col_right, job, commands, commands_1, commands_2, commands_3, commands_4, commands_5
        global b_pos, b_neg, b_align, b_cycle, b_home, b_plus, b_minus, b_preview
        
        yield header
        # yield HotkeyButton('p', 'Press')
        # yield HotkeyButton('x', 'Something')
        with Horizontal():
            with Vertical() as col_left:
                with Vertical() as job:
                    yield job_current
                    yield job_status
                    yield job_progress
                    # yield Rule()
                    with Horizontal(id='commands') as commands:
                        with Vertical() as commands_1:
                            yield (b_pos := HotkeyButton(label='Plot', id="pos"))
                        with Vertical() as commands_2:
                            yield (b_align := HotkeyButton('a', 'Align', label='Align', id='align'))
                            yield (b_cycle := HotkeyButton('c', 'Cycle', label='Cycle', id='cycle'))
                            yield (b_home := HotkeyButton('h', 'Home', label='Home', id='home'))
                        with Vertical() as commands_3:
                            yield (b_plus := HotkeyButton(label='+10', id='plus'))
                            yield (b_minus := HotkeyButton(label='-10', id='minus'))
                        with Vertical() as commands_4:
                            yield (b_preview := HotkeyButton(label='Preview', id='preview'))
                        with Vertical() as commands_5:
                            yield (b_neg := HotkeyButton(label='Cancel', id='neg'))
                yield queue
            with Vertical() as col_right:
                yield log
        yield footer
    
    def on_mount(self):
        self.title = "Plotter"
        header.tall = True
        col_left.styles.width = '3fr'
        col_right.styles.width = '2fr'
        
        # self.query_one('#footer').show_command_palette=False
        log.border_title = 'Log'
        log.styles.border = ('solid', 'white')
        
        job.border_title = 'Job'
        job.styles.border = ('solid', 'white')
        job.styles.height = 22
        
        job_current.styles.height = 3
        job_current.add_columns(*QUEUE_HEADERS)
        job_current.cursor_type = 'none'
        job_status.styles.margin = 1
        job_progress.styles.margin = 1
        job_progress.styles.width = '100%'
        job_progress.query_one('#bar').styles.width = '1fr'
        
        commands.styles.margin = (3, 0, 0, 0)
        
        for button in commands.query('Button'):
            button.styles.width = '100%'
            button.styles.margin = (0, 1);
            
        for col in commands.query('Vertical'):
            col.styles.align_horizontal = 'center'
            # col.styles.border = ('vkey', 'white')
            
        commands_2.styles.width = '0.5625fr'
        for button in commands_2.query('Button'):
            button.styles.min_width = 9
        
        commands_3.styles.width = '0.3125fr'
        for button in commands_3.query('Button'):
            button.styles.min_width = 5
        
        commands_4.styles.width = '0.6875fr'
        for button in commands_4.query('Button'):
            button.styles.min_width = 11
        
        queue.border_title = 'Queue'
        queue.styles.border = ('solid', 'white')
        queue.styles.height = '1fr'
        queue.add_columns(*QUEUE_HEADERS)
        queue.cursor_type = 'row'
        
        self.update_header()
        
        setup_ssl()
        # log.write(log.styles.height)
        
        global server_task
        server_task = asyncio.create_task(run_server(self))
        
        def on_server_task_exit(task):
            print('[red]SERVER TASK EXIT')
            if not task.cancelled():
                ex = task.exception()
                if ex != None:
                    print(ex)
                    raise ex
                    self.quit()
            
        server_task.add_done_callback(on_server_task_exit)
        
        # global spooler_task
        # spooler_task = asyncio.create_task(spooler.start(self))
    
    def on_resize(self, event):
        pass
        
    def on_key(self):
        pass
    
    def print(self, *args, sep=' ', end='\n'):
        if len(args) == 1: log.write(args[0])
        else: log.write( sep.join(map(str, args)) + end)
    
    def update_header(self):
        status = spooler.status()
        self.title = status['status_desc']
        self.sub_title = f'{num_clients} Clients – {spooler.num_jobs()} Jobs'
    
    def bind(self, *args, **kwargs):
        super().bind(*args, **kwargs)
        self.refresh_bindings()
        
    def unbind(self, key):
        # self._bindings.key_to_bindings is a dict of keys to lists of Binding objects
        self._bindings.key_to_bindings.pop(key, None)
        self.refresh_bindings()
    
    # bindings: [ (key, desc), ... ]
    # This not a coroutine (no async). It returns a future, which can be awaited from coroutines
    def prompt(self, bindings, message):
        # setup bindings
        self.print(message)
        self.print(bindings)
        self.update_bindings([ ('y', 'prompt_response("y")', 'Yes'), ('n', 'prompt_response("n")', 'No') ])
        
        # return a future that eventually resolves to the result
        loop = asyncio.get_running_loop()
        self.prompt_future = loop.create_future()
        return self.prompt_future
    
    def preview_job(self, job):
        if job != None and 'save_path' in job:
            print(f'Preview job \\[{job["client"]}]: {job["save_path"]}')
            sub_coro = asyncio.create_subprocess_exec('qlmanage', '-p', job['save_path'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            asyncio.create_task(sub_coro)
    
    def adjust_job_speed(self, job, delta):
        if job != None:
            speed = job['speed'] if 'speed' in job else 100
            speed += delta
            speed = int(speed / 10) * 10
            speed = max( min(speed, 100), 10 )
            print(f'Adjust job speed \\[{job["client"]}]: {speed}')
            job['speed'] = speed
            if (job == spooler.current_job()): self.update_current_job()
    
    @on(Button.Pressed, '#commands Button')
    def on_button(self, event):
        id = event.button.id
        if (id == 'preview'):
            self.preview_job( spooler.current_job() )
            return
        if (id == 'plus'):
            self.adjust_job_speed( spooler.current_job(), 10 )
            return
        if (id == 'minus'):
            self.adjust_job_speed( spooler.current_job(), -10 )
            return
        
        if self.prompt_future != None and not self.prompt_future.done():
            if id == None and event.button.hotkey_description:
                id = str(event.button.hotkey_description).lower()
            if id == None and event.button.label:
                id = str(event.button.label).lower()
            self.prompt_future.set_result({
                'id': id, # use button id, hotkey description (lowercase), or button label (lowercase)
                'button': event.button
            })
            print('PROMPT result', id)
    
    @on(Key)
    async def on_queue_hotkey(self, event):
        if event.key in ['backspace', 'i', 'k', '1', '0']:
            if queue.row_count == 0: return # nothing in list
            client = queue.ordered_rows[queue.cursor_row].key.value
            
            if (event.key == 'backspace'):
                # if this is the current job, and we haven't started, cancel the prompt to start
                if spooler.current_client() == client and spooler.status()['status'] == 'confirm_plot':
                    self.cancel_prompt_ui()
                # handle all other cases (even plots that are running)
                else:
                    await spooler.cancel(client)
            elif (event.key == 'i'):
                await spooler.move(client, max(queue.cursor_row - 1, 0))
                queue.move_cursor(row=queue.get_row_index(client))
            elif (event.key == 'k'):
                new_row = queue.cursor_row + 1
                await spooler.move(client, new_row)
                queue.move_cursor(row=queue.get_row_index(client))
            elif (event.key == '1'):
                await spooler.move(client, 0)
                queue.move_cursor(row=queue.get_row_index(client))
            elif (event.key == '0'):
                await spooler.move(client, -1)
                queue.move_cursor(row=queue.get_row_index(client))
    
    def job_to_row(self, job, idx):
        return (idx, job['client'], job['hash'][:5], job['stats']['count'], job['stats']['layer_count'], int(job['stats']['travel'])/1000, int(job['stats']['travel_ink'])/1000, job['format'], job['speed'], f'{math.floor(job["time_estimate"]/60)}:{round(job["time_estimate"]%60):02}')
        
    def update_current_job(self):
        job = spooler.current_job()
        job_current.clear()
        if job != None:
            job_current.add_row( *self.job_to_row(job, 1), key=job['client'] )
    
    def update_job_queue(self):
        queue.clear()
        for idx, job in enumerate(spooler.jobs()):
            queue.add_row( *self.job_to_row(job, idx+1), key=job['client'] )
    
    def cancel_prompt_ui(self):
        if self.prompt_future != None and not self.prompt_future.done():
            self.prompt_future.cancel()
        
    # This not a coroutine (no async). It returns a future, which can be awaited from coroutines
    def prompt_ui(self, variant, message = ''):
        print('PROMPT', variant)
        
        if len(message) > 0: message = ' – ' + message
        job_status.update(spooler.status()['status_desc'] + message)
        self.update_current_job()
        
        match variant:
            case 'setup':
                b_pos.variant = 'default'
                b_pos.disabled = True
                
                b_neg.update_hotkey('d', 'Done')
                b_neg.variant = 'success'
                b_neg.disabled = False
                
                b_align.disabled = False
                b_cycle.disabled = False
                b_home.disabled = True
                b_plus.disabled = True
                b_minus.disabled = True
                b_preview.disabled = True

            case 'waiting':
                b_pos.disabled = True
                b_neg.disabled = True
                
                b_align.disabled = True
                b_cycle.disabled = True
                b_home.disabled = True
                b_plus.disabled = True
                b_minus.disabled = True
                b_preview.disabled = True
            case 'start_plot':
                b_pos.update_hotkey('p', 'Plot')
                b_pos.variant = 'success'
                b_pos.disabled = False
                
                b_neg.update_hotkey('c', 'Cancel')
                b_neg.variant = 'error'
                b_neg.disabled = False
                
                b_align.disabled = False
                b_cycle.disabled = False
                b_home.disabled = True
                b_plus.disabled = False
                b_minus.disabled = False
                b_preview.disabled = False
            case 'repeat_plot':
                b_pos.update_hotkey('p', 'Plot again')
                b_pos.variant = 'primary'
                b_pos.disabled = False
                
                b_neg.update_hotkey('d', 'Done')
                b_neg.variant = 'success'
                b_neg.disabled = False
                
                b_align.disabled = False
                b_cycle.disabled = False
                b_home.disabled = True
                b_plus.disabled = False
                b_minus.disabled = False
                b_preview.disabled = False
            case 'resume_plot':
                b_pos.update_hotkey('p', 'Resume')
                b_pos.variant = 'primary'
                b_pos.disabled = False
                
                b_neg.update_hotkey('c', 'Cancel')
                b_neg.variant = 'error'
                b_neg.disabled = False
                
                b_align.disabled = False
                b_cycle.disabled = False
                b_home.disabled = False
                b_plus.disabled = True
                b_minus.disabled = True
                b_preview.disabled = False
            case _:
                raise ValueError('Invalid variant')
        
        # return a future that eventually resolves to the result
        # reuse the future if it isn't done. allows for updating the prompt
        if self.prompt_future == None or self.prompt_future.done():
            loop = asyncio.get_running_loop()
            self.prompt_future = loop.create_future()
        return self.prompt_future



if __name__ == "__main__":
    global print
    global tprint
    tprint = print
    
    if USE_PORKBUN:
        porkbun.ddns_update(PORKBUN_ROOT_DOMAIN, PORKBUN_SUBDOMAIN, PORKBUN_TTL)
        porkbun.cert_update(PORKBUN_ROOT_DOMAIN, PORKBUN_SSL_OUTFILE)
        print()
        
    if USE_ZEROCONF: zc.add_zeroconf_service(ZEROCONF_HOSTNAME, PORT)
    
    app = App()
    print = app.print
    
    app.run()