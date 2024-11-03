import asyncio
from pyaxidraw import axidraw
from datetime import datetime, timezone
import math
import os
from capture_output import capture_output
import re
import hashlib
import async_queue

FOLDER_WAITING  ='svgs/0_waiting'
FOLDER_CANCELED ='svgs/1_canceled'
FOLDER_FINISHED ='svgs/2_finished'
PEN_POS_UP = 60 # Default: 60
PEN_POS_DOWN = 40 # Default: 40
MIN_SPEED = 10 # percent

KEY_DONE = ( 'd', '(D)one' )
KEY_REPEAT = ( 'r', '(R)epeat' )
KEY_START_PLOT = ( 'p', '(P)lot' )
KEY_RESTART_PLOT = ( 'p', '(P)lot from start' )
KEY_ALIGN = ( 'a', '(A)lign' )
KEY_CYCLE = ( 'c', '(C)ycle' )
KEY_CANCEL = ( chr(27), '(Esc) Cancel Job' )
KEY_RESUME = ( 'r', '(R)esume' )
KEY_HOME = ( 'h', '(H)ome' )

STATUS_DESC = {
    'setup': 'Setting up',
    'waiting': 'Waiting for jobs',
    'confirm_plot': 'Confirm job',
    'plotting': 'Plotting'
}

TESTING = True # Don't actually connect to AxiDraw, just simulate plotting
REPEAT_JOBS = True # Ask to repeat a plot after a sucessful print
RESUME_QUEUE = True # Resume plotting queue after quitting/restarting
ALIGN_AFTER = True # Align plotter after success or error
ALIGN_AFTER_PAUSE = False # Align plotter after pause (programmatic, stop button, keyboard interrupt)

queue_size_cb = None
# queue = asyncio.Queue() # an async FIFO queue
queue = async_queue.Queue() # an async FIFO queue that can be reordered
_jobs = {} # an index to all unfinished jobs by client id (in queue or current_job) (insertion order is preserved in dict since python 3.7)
_current_job = None
_status = 'setup' # setup | waiting | confirm_plot | plotting

async def callback(fn, *args):
    if callable(fn):
        await fn(*args)

async def _notify_queue_positions():
    cbs = []
    for i, client in enumerate(_jobs):
        job = _jobs[client]
        if i == 0 and _status == 'plotting': i = -1
        if 'position_notified' not in job or job['position_notified'] != i:
            job['position_notified'] = i
            cbs.append( callback(job['queue_position_cb'], i, job) )
    await asyncio.gather(*cbs) # run callbacks concurrently

async def _notify_queue_size():
    await callback(queue_size_cb, len(_jobs))

def set_queue_size_cb(cb):
    global queue_size_cb
    queue_size_cb = cb

def num_jobs():
    return len(_jobs)

def current_job():
    return _current_job

def jobs():
    # return list(_jobs.values())
    queued = queue.list()
    if (_current_job != None and not _current_job['cancel']):
        queued.insert(0, _current_job)
    return queued
    

def status():
    return {
        'status': _status,
        'status_desc': STATUS_DESC[_status],
        'job': _current_job['client'] if _current_job != None else None,
        'job_str': job_str(_current_job) if _current_job != None else None,
        'queue_size': num_jobs(),
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
            job['save_path'] = file
        else:
            try:
                os.remove(file)
            except:
                pass
    return True
    
def save_svg_async(*args, **kwargs):
    return asyncio.to_thread(save_svg, *args, **kwargs)


# Updated pre version 4 SVGs, so they are compatible with resume queue
def update_svg(job):
    match = re.search('tg:version="(\\d+)"', job['svg'])
    if match != None and int(match.group(1)) >= 4: return
    
    MARKER = 'xmlns:tg="https://sketch.process.studio/turtle-graphics"'
    idx = job['svg'].find(MARKER)
    if idx == -1: return
    idx += len(MARKER)
    insert = f'\n     tg:version="4" tg:layer_count="1" tg:oob_count="{job['stats']['oob_count']}" tg:short_count="{job['stats']['short_count']}" tg:format="{job['format']}" tg:width_mm="{job['size'][0]}" tg:height_mm="{job['size'][1]}" tg:speed="{job['speed']}" tg:author="{job['client']}" tg:timestamp="{job['timestamp']}"'
    
    job['svg'] = job['svg'][:idx] + insert + job['svg'][idx:]
    job['hash'] = hashlib.sha1(job['svg'].encode('utf-8')).hexdigest()

# job {'type': 'plot, 'client', 'id', 'svg', stats, timestamp, hash, speed, format, size, received?}
# adds to job: { 'cancel', time_estimate', 'layers', received }
# todo: don't wait on callbacks
async def enqueue(job, queue_position_cb = None, done_cb = None, cancel_cb = None, error_cb = None):
    # the client might be in queue (or currently plotting)
    if job['client'] in _jobs:
        await callback( error_cb, 'Cannot add job, you already have a job queued!', job )
        return False
    
    job['cancel'] = False
    # save callbacks
    job['queue_position_cb'] = queue_position_cb
    job['done_cb'] = done_cb
    job['cancel_cb'] = cancel_cb
    job['error_cb'] = error_cb
    if 'received' not in job or job['received'] == None:
        job['received'] = timestamp()
    
    # speed
    if 'speed' in job: job['speed'] = max( min(job['speed'], 100), MIN_SPEED ) # limit speed  (MIN_SPEED, 100)
    else: job['speed'] = 100
    # format
    if 'format' not in job: job['format'] = 'A3_LANDSCAPE'
    
    # add to jobs index
    _jobs[ job['client'] ] = job
    print(f'New job \\[{job["client"]}] {job["hash"][0:5]}')
    sim = await simulate_async(job) # run simulation
    job['time_estimate'] = sim['time_estimate']
    job['layers'] = sim['layers']
    
    update_svg(job)
    await queue.put(job)
    await save_svg_async(job, 'waiting')
    
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions()
    return True

async def cancel(client, force = False):
    if not force:
        if _current_job != None and _current_job['client'] == client:
            await callback( _current_job['error_cb'], 'Cannot cancel, already plotting!', _current_job )
            return False
    
    if client not in _jobs: return False
    job = _jobs[client]
    job['cancel'] = True # set cancel flag
    del _jobs[client] # remove from index
    
    # TODO: if current job, its not in the queue anymore
    
    await callback( job['cancel_cb'], job ) # notify canceled job
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions() # notify queue positions (might have changed for some)
    print(f'❌ [red]Canceled job \\[{job["client"]}]')
    await save_svg_async(job, 'canceled')
    return True

async def cancel_current_job(force = True):
    print('call cancel job')
    return await cancel(_current_job['client'], force = force)

async def finish_current_job():
    await callback( _current_job['done_cb'], _current_job ) # notify job done
    del _jobs[ _current_job['client'] ] # remove from jobs index
    await _notify_queue_positions() # notify queue positions. current job is 0
    await _notify_queue_size() # notify queue size
    print(f'✅ [green]Finished job \\[{_current_job["client"]}]')
    _status = 'waiting'
    await save_svg_async(_current_job, 'finished')
    return True

def job_str(job):
    info = '[' + str(job["client"])[0:10] + '] ' + job['hash'][0:5]
    speed_and_format = f'{job["speed"]}%, {job["format"]}, {math.floor(job["time_estimate"]/60)}:{round(job["time_estimate"]%60):02} min'
    if 'stats' in job:
        stats = job['stats']
        layers = f'{job["layers"]} layers, ' if 'layers' in job and job['layers'] > 1 else ''
        if 'count' in stats and 'travel' in stats and 'travel_ink' in stats:
            info += f' ({stats["count"]} lines, {layers}{int(stats["travel_ink"])}/{int(stats["travel"])} mm, {speed_and_format})'
    else:
        info += f' ({speed_and_format})'
    return info


# Return codes
PLOTTER_ERRORS = {
    0: 'No error; operation nominal',
    1: 'Paused programmatically',
    101: 'Failed to connect',
    102: 'Stopped by pause button press',
    103: 'Stopped by keyboard interrupt',
    104: 'Lost USB connectivity'
}
PLOTTER_PAUSED = [ 1, 102, 103 ];

def get_error_msg(code):
    if code in PLOTTER_ERRORS:
        return PLOTTER_ERRORS[code]
    else:
        return f'Unkown error (Code {code})'

def print_axidraw(*args):
    out = ' '.join(args)
    lines = out.split('\n')
    for line in lines:
        print(f"[gray50]\\[AxiDraw] " + line)

# Raise pen and disable XY stepper motors
def align():
    with capture_output(print_axidraw, print_axidraw):
        ad = axidraw.AxiDraw()
        ad.plot_setup()
        ad.options.mode = 'align' # A setup mode: Raise pen, disable XY stepper motors
        ad.options.pen_pos_up = PEN_POS_UP
        ad.options.pen_pos_down = PEN_POS_DOWN
        if TESTING: ad.options.preview = True
        ad.plot_run()
    return ad.errors.code

# Cycle the pen down and back up
def cycle():
    with capture_output(print_axidraw, print_axidraw):
        ad = axidraw.AxiDraw()
        ad.plot_setup()
        ad.options.mode = 'cycle' # A setup mode: Lower and then raise the pen
        ad.options.pen_pos_up = PEN_POS_UP
        ad.options.pen_pos_down = PEN_POS_DOWN
        if TESTING: ad.options.preview = True
        ad.plot_run()
    return ad.errors.code

def plot(job, align_after = ALIGN_AFTER, align_after_pause = ALIGN_AFTER_PAUSE, options_cb = None, return_ad = False):
    if 'svg' not in job: return 0
    speed = job['speed'] / 100
    with capture_output(print_axidraw, print_axidraw):
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
        if callable(options_cb): options_cb(ad.options)
        if TESTING: ad.options.preview = True
        job['output_svg'] = ad.plot_run(output=True)
    if (ad.errors.code in PLOTTER_PAUSED and align_after_pause) or \
       (ad.errors.code not in PLOTTER_PAUSED and align_after):
        align()
    if return_ad: return ad
    else: return ad.errors.code

def resume_home(job, align_after = ALIGN_AFTER, align_after_pause = ALIGN_AFTER_PAUSE, options_cb = None, return_ad = False):
    if 'output_svg' not in job: return 0
    orig_svg = job['svg'] # save original svg
    job['svg'] = job['output_svg'] # set last output svg as input
    
    def _options_cb(options):
        if callable(options_cb): options_cb(options)
        options.mode = 'res_home'
    
    res = plot(job, align_after, align_after_pause, _options_cb, return_ad)
    job['svg'] = orig_svg # restore original svg
    return res

def resume_plot(job, align_after = ALIGN_AFTER, align_after_pause = ALIGN_AFTER_PAUSE, options_cb = None, return_ad = False):
    if 'output_svg' not in job: return 0
    orig_svg = job['svg'] # save original svg
    job['svg'] = job['output_svg'] # set last output svg as input
    
    def _options_cb(options):
        if callable(options_cb): options_cb(options)
        options.mode = 'res_plot'
    
    res = plot(job, align_after, align_after_pause, _options_cb, return_ad)
    job['svg'] = orig_svg # restore original svg
    return res

def simulate(job):
    if 'svg' not in job: return 0
    speed = job['speed'] / 100
    
    stats = {
        'error_code': None,
        'time_estimate': 0,
        'distance_total': 0,
        'distance_pendown': 0,
        'pen_lifts': 0,
        'layers': 0
    }
    
    def update_stats(ad):
        stats['error_code'] = ad.errors.code
        stats['time_estimate'] += ad.time_estimate
        stats['distance_total'] += ad.distance_total
        stats['distance_pendown'] += ad.distance_pendown
        stats['pen_lifts'] += ad.pen_lifts
        stats['layers'] += 1
    
    def _options_cb(options):
        options.preview = True
    
    ad = plot(job, align_after=False, align_after_pause=False, options_cb=_options_cb, return_ad=True)
    update_stats(ad)
    
    while ad.errors.code == 1: # Paused programmatically
        ad = resume_plot(job, align_after=False, align_after_pause=False, options_cb=_options_cb, return_ad=True)
        update_stats(ad)
    
    return stats


async def plot_async(*args, **kwargs):
    return await asyncio.to_thread(plot, *args, **kwargs)

async def simulate_async(*args, **kwargs):
    return await asyncio.to_thread(simulate, *args, **kwargs)

async def align_async():
    return await asyncio.to_thread(align)

async def cycle_async():
    return await asyncio.to_thread(cycle)

async def resume_plot_async(*args, **kwargs):
    return await asyncio.to_thread(resume_plot, *args, **kwargs)

async def resume_home_async(*args, **kwargs):
    return await asyncio.to_thread(resume_home, *args, **kwargs)

async def prompt_setup(message = 'Press \'Done\' when ready'):
    while True:
        res = await prompt_ui('setup', message)
        res = res['id']
        if res == 'align': # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == 'cycle': # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == 'neg' : # Finish
            return True

async def prompt_start_plot(message):
    while True:
        res = await prompt_ui('start_plot', message)
        res = res['id']
        if res == 'pos': # Start Plot
            return True
        elif res == 'align': # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == 'cycle': # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == 'neg': # Cancel
            return False

async def prompt_repeat_plot(message):
    while True:
        res = await prompt_ui('repeat_plot', message)
        res = res['id']
        if res == 'pos': # Start Plot
            return True
        elif res == 'align': # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == 'cycle': # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == 'neg': # Done
            return False

async def prompt_resume_plot(message, job):
    while True:
        res = await prompt_ui('resume_plot', message)
        res = res['id']
        
        if res == 'pos': # Resume Plot
            return True
        elif res == 'home': # Home
            print('Returning home...')
            await resume_home_async(job) # -> prompt again
        elif res == 'align': # Align
            print('Aligning...')
            await align_async() # -> prompt again
        elif res == 'cycle': # Cycle
            print('Cycling...')
            await cycle_async() # -> prompt again
        elif res == 'neg': # Done
            return False

async def resume_queue():
    import xml.etree.ElementTree as ElementTree
    list = sorted(os.listdir(FOLDER_WAITING))
    list = [ os.path.join(FOLDER_WAITING, x) for x in list if x.endswith('.svg') ]
    resumable_jobs = []
    for filename in list:
        # print('Loading ', filename)
        try:
            with open(filename, 'r') as file:
                svg = file.read()
            root = ElementTree.fromstring(svg)
            def attr(attr, ns = 'https://sketch.process.studio/turtle-graphics'):
                return root.get(attr if ns == None else "{" + ns + "}" + attr)
            match = re.search('\\d{8}_\\d{6}.\\d{6}_UTC[+-]\\d{4}', os.path.basename(filename))
            received_ts = None if match == None else match.group(0)
            job = {
                'loaded_from_file': True,
                'client': attr('author'),
                'id': "XYZ",
                'svg': svg,
                'stats': {
                    'count': int(attr('count')),
                    'layer_count': int(attr('layer_count')),
                    'oob_count': int(attr('oob_count')),
                    'short_count': int(attr('short_count')),
                    'travel': int(attr('travel')),
                    'travel_ink': int(attr('travel_ink')),
                    'travel_blank': int(attr('travel_blank'))
                },
                'timestamp': attr('timestamp'),
                'speed': int(attr('speed')),
                'format': attr('format'),
                'size': [int(attr('width_mm')), int(attr('height_mm'))],
                'hash': hashlib.sha1(svg.encode('utf-8')).hexdigest(),
                'received': received_ts
            }
            resumable_jobs.append(job)
        except:
            print('Error resuming ', filename)
    
    if len(resumable_jobs) > 0: print(f"Resuming {len(resumable_jobs)} jobs...")
    else: print("No jobs to resume")
    for job in resumable_jobs:
        await enqueue(job)


def set_status(status):
    global _status
    _status = status
    print_status()

async def start(app):
    global _current_job
    global _status
    
    global print
    print = app.print
    
    global prompt_ui
    prompt_ui = app.prompt_ui
    
    global print_status
    print_status = app.update_header
    
    if TESTING: print('[yellow]TESTING MODE enabled')
    # if RESUME_QUEUE: await resume_queue()
    
    
    await align_async()
    await prompt_setup()
    
    while True:
        # get the next job from the queue, waits until a job becomes available
        if queue.empty():
            set_status('waiting')
            prompt_ui('waiting')
        _current_job = await queue.get()
        
        if not _current_job['cancel']: # skip if job is canceled
            set_status('confirm_plot')
            ready = await prompt_start_plot(f'Ready to plot job \\[{_current_job["client"]}] ?')
            if not ready:
                await cancel_current_job()
                set_status('waiting')
                _current_job = None
                continue # skip over rest of the loop
            
            # plot (and retry on error or repeat)
            loop = 0 # number or tries/repetitions
            resume = False # flag indicating resume (vs. plotting from start)
            while True:
                if (resume):
                    print(f'🖨️  [yellow]Resuming job \\[{_current_job["client"]}] ...')
                    _status = 'plotting'
                    error = await resume_plot_async(_current_job)
                else:
                    loop += 1
                    print(f'🖨️  [yellow]Plotting job \\[{_current_job["client"]}] ...')
                    _status = 'plotting'
                    await _notify_queue_positions() # notify plotting
                    error = await plot_async(_current_job)
                resume = False
                # No error
                if error == 0:
                    if REPEAT_JOBS:
                        print(f'[blue]Done ({loop}x) job \\[{_current_job["client"]}]')
                        set_status('confirm_plot')
                        repeat = await prompt_repeat_plot(f'Repeat ({loop+1}) job \\[{_current_job["client"]}] ?')
                        if repeat: continue
                    await finish_current_job()
                    break
                # Paused programmatically (1), Stopped by pause button press (102) or Stopped by keyboard interrupt (103)
                elif error in PLOTTER_PAUSED:
                    print(f'[yellow]Plotter: {get_error_msg(error)}')
                    set_status('plotting')
                    ready = await prompt_resume_plot(f'[yellow]Resume[/yellow] job \\[{_current_job["client"]}] ?', _current_job)
                    if not ready:
                        await cancel_current_job()
                        break
                    if ready: resume = True
                # Errors
                else:
                    print(f'[red]Plotter: {get_error_msg(error)}')
                    set_status('confirm_plot')
                    ready = await prompt_start_plot(f'[red]Retry job \\[{_current_job["client"]}] ?')
                    if not ready:
                        await cancel(_current_job['client'], force = True)
                        break
                        
            _status = 'waiting'
        _current_job = None
