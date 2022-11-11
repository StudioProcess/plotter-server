import asyncio
import sys
import termios
import tty

# async prompt for a single keystroke
class AsyncPrompt:
    def __init__(self):
        self.echo = True
        self.echo_end = '\n'
        self.waiting_for_input = False
        self.queue = asyncio.Queue()
        asyncio.get_running_loop().add_reader(sys.stdin, self.on_input)

    def on_input(self):
        if self.waiting_for_input:
            key = sys.stdin.read(1)
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_ttyattrs)
            if ord(key) == 3: # catch Control-C
                raise KeyboardInterrupt()
            if self.echo:
                print(key, end=self.echo_end) # echo the input character (with newline)
            # print('got input:', key)
            self.queue.put_nowait(key)
            self.waiting_for_input = False
        else:
            input = sys.stdin.readline() # discard input
            # print('discard input:', input)
    
    async def prompt(self, message = '? ', echo = True, echo_end = '\n'):
        self.echo = echo
        # print prompt
        print(message, end = '', flush=True)
        # set raw input mode on tty
        self.old_ttyattrs = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
        # set flag to capture input
        self.waiting_for_input = True
        # wait until input is received
        return await self.queue.get()
    
    async def wait_for(self, chars, message = '? ', echo = True, echo_end = '\n'):
        chars = list(map(lambda ch: chr(ch) if type(ch) == int else ch, chars))
        
        res = None
        while res not in chars:
            res = await self.prompt(message, echo)
        return res