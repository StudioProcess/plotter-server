import asyncio
from pyaxidraw import axidraw

SIMULATE_PLOT_TIME = 10

queue_size_cb = None
queue = asyncio.Queue() # an async FIFO queue 
jobs = {} # an index to all unfinished jobs by client id (in queue or current_job) (insertion order is preserved in dict since python 3.7)
current_job = None
_status = 'waiting' # waiting | confirm_plot | plotting

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
        'queue_size': queue_size(),
    }



# job: 'client', 'lines'
# todo: don't wait on callbacks
async def enqueue(job, queue_position_cb = None, done_cb = None, cancel_cb = None, error_cb = None):
    # the client might be in queue (or currently plotting)
    if job['client'] in jobs:
        await callback( error_cb, 'cannot add job, you already have a job queued', job )
        return False
    
    job['cancel'] = False
    # save callbacks
    job['queue_position_cb'] = queue_position_cb
    job['done_cb'] = done_cb
    job['cancel_cb'] = cancel_cb
    job['error_cb'] = error_cb
    
    # add to jobs index
    jobs[ job['client'] ] = job
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions()
    await queue.put(job)
    print(f'New job {job["client"]}')
    return True

async def cancel(client, force = False):
    print('canceling ')
    if not force:
        if current_job != None and current_job['client'] == client:
            await callback( current_job['error_cb'], 'cannot cancel, already plotting', current_job )
            return False
    
    if client not in jobs: return False
    job = jobs[client]
    job['cancel'] = True # set cancel flag 
    del jobs[client] # remove from index
    
    await callback( job['cancel_cb'], job ) # notify canceled job
    await _notify_queue_size() # notify new queue size
    await _notify_queue_positions() # notify queue positions (might have changed for some)
    print(f'Canceled job {job["client"]}')
    return True



def align():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = 'align' # A setup mode: Raise pen, disable XY stepper motors
    ad.plot_run()
    return ad.errors.code

# Return codes:
# 0	  .. No error; operation nominal
# 101 .. Failed to connect
# 102 .. Stopped by pause button press
# 103 .. Stopped by keyboard interrupt (if enabled)
# 104 .. Lost USB connectivity
def plot(job, align_after = True):
    ad = axidraw.AxiDraw()
    ad.plot_setup(job['svg'])
    ad.options.model = 2 # A3
    ad.options.reordering = 4 # no reordering
    ad.options.speed_pendown = 110
    ad.options.speed_penup = 110
    ad.options.accel = 100
    ad.options.pen_rate_lower = 100
    ad.options.pen_rate_raise = 100
    ad.plot_run()
    if align_after: align()
    return ad.errors.code

async def plot_async(*args):
    return await asyncio.to_thread(plot, *args)

async def align_async():
    return await asyncio.to_thread(align)



async def start(prompt, print_status):
    global current_job
    global _status
    global print
    print = prompt.print # replace global print function
    
    await align_async()
    
    while True:
        # get the next job from the queue, waits until a job becomes available
        if queue.empty(): 
            print_status()
        current_job = await queue.get()
        if not current_job['cancel']: # skip if job is canceled
            _status = 'confirm_plot'
            print_status()
            res = await prompt.wait_for( [13, 'c'], f'Ready to plot job {current_job["client"]} (Press Return to start, C to cancel)? ', echo=True)
            if res == 'c': # cancel
                await cancel(current_job['client'], force = True)
                _status = 'waiting'
                continue # skip over rest of the loop
            
            print(f'Plotting job {current_job["client"]}...')
            _status = 'plotting'
            await _notify_queue_positions() # notify plotting
            print_status()
            await plot_async(current_job)
            print(f'Finished job {current_job["client"]}')
            _status = 'waiting'
            
            await callback( current_job['done_cb'], current_job ) # notify job done
            del jobs[ current_job['client'] ] # remove from jobs index
            await _notify_queue_positions() # notify queue positions. current job is 0
            await _notify_queue_size() # notify queue size
        current_job = None
