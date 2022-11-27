import os
import os.path
import asyncio
import threading

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

def read_fifo_sync():
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)
    while True:
        print("Waiting for fifo...")
        data = read_fifo_once()
        print(f"Got: {data}")

async def read_fifo():
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)
    quit = False
    while not quit:
        print("Waiting for fifo...")
        try:
            data = await asyncio.to_thread(read_fifo_once)
            print(f"Got: {data}")
        except:
            print('abort read_fifo_once')
            quit = True
    

async def main():
    # await asyncio.gather(
    #     idle(),
    #     read_fifo()
    # )
    await read_fifo()
    print('done main')

if __name__ == '__main__':
    try:
        asyncio.run(main())
        print('done run')
        # read_fifo_sync()
    except KeyboardInterrupt:
        pass
    print('Quitting.')
    print(asyncio.get_running_loop())
    print(threading.active_count())
    