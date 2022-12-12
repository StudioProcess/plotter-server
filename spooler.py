import asyncio
from pyaxidraw import axidraw
from tty_colors import COL
from datetime import datetime, timezone
import os

FOLDER_WAITING  ='svgs/0_waiting'
FOLDER_CANCELED ='svgs/1_canceled'
FOLDER_FINISHED ='svgs/2_finished'
PEN_POS_UP = 60 # Default: 60
PEN_POS_DOWN = 45 # Default: 40
MIN_SPEED = 10 # percent

KEY_DONE = [ 'd', '(D)one' ]
KEY_REPEAT = [ 'r', '(R)epeat' ]
KEY_START_PLOT = [ 'p', '(P)lot' ]
KEY_ALIGN = [ 'a', '(A)lign' ]
KEY_CYCLE = [ 'c', '(C)ycle' ]
KEY_CANCEL = [ chr(27), '(Esc) Cancel Job' ]

REPEAT_JOBS = True # Ask to repeat a plot after a sucessful print


queue_size_cb = None
queue = asyncio.Queue() # an async FIFO queue 
jobs = {} # an index to all unfinished jobs by client id (in queue or current_job) (insertion order is preserved in dict since python 3.7)
current_job = None
_status = 'setup' # setup | waiting | confirm_plot | plotting

async def callback(fn, *args):
    if callable(fn):
        await fn(*args)

async def _notify_queue_positions():
    cbs = []
    for i, client in enumerate(jobs):
        job = jobs[client]
        if i == 0 and _status == 'plotting': i = -1
        if 'position_notified' not in job or job['position_notified'] != i:
            job['position_notified'] = i
            cbs.append( callback(job['queue_position_cb'], i, job) )
    await asyncio.gather(*cbs) # run callbacks concurrently

async def _notify_queue_size():
    await callback(queue_size_cb, len(jobs))

def set_queue_size_cb(cb):
    global queue_size_cb
    queue_size_cb = cb

def queue_size():
    return len(jobs)

def status():
    return {
        'status': _status,
        'job': current_job['client'] if current_job != None else None,
        'job_str': job_str(current_job) if current_job != None else None,
        'queue_size': queue_size(),
    }

def timestamp(date = None):
    if date == None: 
        # make timezone aware timestamp: https://stackoverflow.com/a/39079819
        date = datetime.now(timezone.utc)
        date = date.replace(tzinfo=date.astimezone().tzinfo)
    return date.strftime("%Y%m%d_%H%M%S.%f_UTC%z")

# status: 'waiting' | 'canceled' | 'finished'
def save_svg(job, status):
    if status not in ['waiting', 'canceled', 'finished']:
        return False
    filename = f'{job["received"]}_{job["client"][0:10]}_{job["hash"][0:5]}.svg'
    files = {
        'waiting': os.path.join(FOLDER_WAITING, filename),
        'canceled': os.path.join(FOLDER_CANCELED, filename),
        'finished': os.path.join(FOLDER_FINISHED, filename),
    }
    for key, file in files.items():
        if key == status:
            os.makedirs( os.path.dirname(file), exist_ok=True)
            with open(file, 'w', encoding='utf-8') as f: f.write(job['svg'])
        else:
            try:
                os.remove(file)
            except:
                pass
    return True
    
def save_svg_async(*args):
    return asyncio.to_thread(save_svg, *args)

# job: 'client', 'lines'
# todo: don't wait on callbacks
async def enqueue(job, queue_position_cb = None, done_cb = None, cancel_cb = None, error_cb = None):
    # the client might be in queue (or currently plotting)
    if job['client'] in jobs:
        await callback( error_cb, 'Cannot add job, you already have a job queued!', job )
        return False
    
    job['cancel'] = False
    # save callbacks
    job['queue_position_cb'] = queue_position_cb
    job['done_cb'] = done_cb
    job['cancel_cb'] = cancel_cb
    job['error_cb'] = error_cb
    job['received'] = timestamp()
    
    # speed 
    if 'speed' in job: job['speed'] = max( min(job['speed'], 100), MIN_SPEED ) # limit speed  (MIN_SPEED, 100)
    else: job['speed'] = 100
    # format
    if 'format' not in job: job['format'] = 'A3_LANDSCAPE'
    
    # add to jobs index
    jobs[ job['client'] ] = job
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions()
    await queue.put(job)
    print(f'New job {job["client"]}')
    await save_svg_async(job, 'waiting')
    return True

async def cancel(client, force = False):
    if not force:
        if current_job != None and current_job['client'] == client:
            await callback( current_job['error_cb'], 'Cannot cancel, already plotting!', current_job )
            return False
    
    if client not in jobs: return False
    job = jobs[client]
    job['cancel'] = True # set cancel flag 
    del jobs[client] # remove from index
    
    await callback( job['cancel_cb'], job ) # notify canceled job
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions() # notify queue positions (might have changed for some)
    print(f'❌ {COL.RED}Canceled job [{job["client"]}]{COL.OFF}')
    await save_svg_async(job, 'canceled')
    return True

async def finish_current_job():
    await callback( current_job['done_cb'], current_job ) # notify job done
    del jobs[ current_job['client'] ] # remove from jobs index
    await _notify_queue_positions() # notify queue positions. current job is 0
    await _notify_queue_size() # notify queue size
    print(f'✅ {COL.GREEN}Finished job [{current_job["client"]}]{COL.OFF}')
    _status = 'waiting'
    await save_svg_async(current_job, 'finished')
    return True

def job_str(job):
    info = '[' + str(job["client"])[0:10] + ']'
    speed_and_format = f'{job["speed"]}%, {job["format"]}'
    if 'stats' in job:
        stats = job['stats']
        if 'count' in stats and 'travel' in stats and 'travel_ink' in stats:
            info += f' ({stats["count"]} lines, {int(stats["travel_ink"])}/{int(stats["travel"])} mm, {speed_and_format})'
    else:
        info += f' ({speed_and_format})'
    return info


# Return codes
PLOTTER_ERRORS = {
    0: 'No error; operation nominal',
    101: 'Failed to connect',
    102: 'Stopped by pause button press',
    103: 'Stopped by keyboard interrupt',
    104: 'Lost USB connectivity'
}

# Raise pen and disable XY stepper motors
def align():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = 'align' # A setup mode: Raise pen, disable XY stepper motors
    ad.options.pen_pos_up = PEN_POS_UP
    ad.options.pen_pos_down = PEN_POS_DOWN
    ad.plot_run()
    return ad.errors.code

# Cycle the pen down and back up
def cycle():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = 'cycle' # A setup mode: Lower and then raise the pen
    ad.options.pen_pos_up = PEN_POS_UP
    ad.options.pen_pos_down = PEN_POS_DOWN
    ad.plot_run()
    return ad.errors.code

def plot(job, align_after = True):
    if 'svg' not in job: return 0
    speed = job['speed'] / 100
    ad = axidraw.AxiDraw()
    ad.plot_setup(job['svg'])
    ad.options.model = 2 # A3
    ad.options.reordering = 4 # No reordering
    ad.options.auto_rotate = True # (This is the default) Drawings that are taller than wide will be rotated 90 deg to the left
    ad.options.speed_pendown = int(110 * speed)
    ad.options.speed_penup = int(110 * speed)
    ad.options.accel = int(100 * speed)
    ad.options.pen_rate_lower = int(100 * speed)
    ad.options.pen_rate_raise = int(100 * speed)
    ad.options.pen_pos_up = PEN_POS_UP
    ad.options.pen_pos_down = PEN_POS_DOWN
    ad.plot_run()
    if align_after: align()
    return ad.errors.code

async def plot_async(*args):
    return await asyncio.to_thread(plot, *args)

async def align_async():
    return await asyncio.to_thread(align)

async def cycle_async():
    return await asyncio.to_thread(cycle)
    

async def prompt_start_plot(message):
    message += f' {KEY_START_PLOT[1]}, {KEY_ALIGN[1]}, {KEY_CYCLE[1]}, {KEY_CANCEL[1]} ?'
    while True:
        res = await prompt.wait_for( [KEY_START_PLOT[0],KEY_ALIGN[0],KEY_CYCLE[0],KEY_CANCEL[0]], message, echo=True )
        if res == KEY_START_PLOT[0]: # Start Plot
            return True
        elif res == KEY_ALIGN[0]: # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == KEY_CYCLE[0]: # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == KEY_CANCEL[0]: # Cancel
            return False

async def prompt_repeat_plot(message):
    message += f' {KEY_REPEAT[1]}, {KEY_ALIGN[1]}, {KEY_CYCLE[1]}, {KEY_DONE[1]} ?'
    while True:
        res = await prompt.wait_for( [KEY_REPEAT[0],KEY_ALIGN[0],KEY_CYCLE[0],KEY_DONE[0]], message, echo=True )
        if res == KEY_REPEAT[0]: # Start Plot
            return True
        elif res == KEY_ALIGN[0]: # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == KEY_CYCLE[0]: # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == KEY_DONE[0]: # Finish
            return False

async def prompt_setup(message = 'Setup Plotter:'):
    message += f' {KEY_ALIGN[1]}, {KEY_CYCLE[1]}, {KEY_DONE[1]} ?'
    while True:
        res = await prompt.wait_for( [KEY_ALIGN[0],KEY_CYCLE[0],KEY_DONE[0]], message, echo=True )
        if res == KEY_ALIGN[0]: # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == KEY_CYCLE[0]: # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == KEY_DONE[0] : # Finish
            return True



async def start(_prompt, print_status):
    global current_job
    global _status
    global print
    global prompt
    prompt = _prompt # make this global
    print = prompt.print # replace global print function
    
    await align_async()
    await prompt_setup()
    _status = 'waiting'
    
    while True:
        # get the next job from the queue, waits until a job becomes available
        if queue.empty(): 
            print_status()
        current_job = await queue.get()
        if not current_job['cancel']: # skip if job is canceled
            _status = 'confirm_plot'
            print_status()
            ready = await prompt_start_plot(f'Ready to plot job {job_str(current_job)}?')
            if not ready:
                await cancel(current_job['client'], force = True)
                _status = 'waiting'
                continue # skip over rest of the loop
            
            # plot (and retry on error or repeat)
            loop = 0 # number or tries/repetitions
            while True:
                loop += 1
                print(f'🖨️  {COL.YELLOW}Plotting job [{current_job["client"]}] ...{COL.OFF}')
                _status = 'plotting'
                await _notify_queue_positions() # notify plotting
                error = await plot_async(current_job)
                if error != 0: # no error
                    if REPEAT_JOBS:
                        print(f'{COL.BLUE}Done ({loop}x) job [{current_job["client"]}]{COL.OFF}')
                        _status = 'confirm_plot'
                        repeat = await prompt_repeat_plot(f'{COL.BLUE}Repeat{COL.OFF} job [{current_job["client"]}] ?')
                        if repeat: continue
                    await finish_current_job()
                    break
                else:
                    col = COL.YELLOW if error in [102,103] else COL.RED
                    print(f'{col}Plotter: {PLOTTER_ERRORS[error]}{COL.OFF}')
                    _status = 'confirm_plot'
                    ready = await prompt_start_plot(f'{col}Retry{COL.OFF} job [{current_job["client"]}] ?')
                    if not ready:
                        await cancel(current_job['client'], force = True)
                        break

            _status = 'waiting'
        current_job = None
