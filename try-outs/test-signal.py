import os
import os.path
import asyncio
import signal
import traceback

# https://stackoverflow.com/a/71420261

FIFO='./fifo'

async def idle():
    n = 0
    while True:
        print(f"Idling ({n})...")
        await asyncio.sleep(5)
        n += 1

def read_fifo_once():
        with open(FIFO) as f:
            data = f.read().strip()
        return data

async def read_fifo():
        if not os.path.exists(FIFO):
            os.mkfifo(FIFO)
        quit = False
        while not quit:
            try:
                print("Waiting for fifo...")
                await asyncio.to_thread(read_fifo_once)
                print(f"Got: {data}")
            except asyncio.exceptions.CancelledError:
                print("Abort read_fifo")
                bump_fifo() # this causes the thread running read_fifo_once to end
                quit = True
        print("end read_fifo ")

def bump_fifo():
    with open(FIFO, 'w') as f:
        f.write('\n')

async def main():
    # await asyncio.gather(
    #     idle(),
    #     read_fifo()
    # )
    await read_fifo()
    print("done read_fifo")

    
    # await idle(
    print('end main')

if __name__ == '__main__':
    try:
        asyncio.run(main())
        print('done run')
        # print(dir(signal.Signals))
    except KeyboardInterrupt:
        pass
    print('Quitting')
    