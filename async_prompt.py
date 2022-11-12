import asyncio
import sys
import termios
import tty
import builtins

# async prompt for a single keystroke
class AsyncPrompt:
    def __init__(self):
        self.echo = True
        self.echo_end = '\n'
        self.waiting_for_input = False
        self.queue = asyncio.Queue()
        asyncio.get_running_loop().add_reader(sys.stdin, self.on_input)
    
    def tty_input(self):
        fd = sys.stdin.fileno()
        self.original_ttyattrs = termios.tcgetattr(fd) # save ttyattrs
        tty.setraw(fd) # set raw input mode on tty
    
    def tty_restore(self):
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, self.original_ttyattrs)
    
    def on_input(self):
        if self.waiting_for_input:
            key = sys.stdin.read(1)
            self.tty_restore()
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
        self.tty_input()
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
    
    def print(self, *objects, sep=' ', end='\n', file=None, flush=False):
        if self.waiting_for_input:
            self.tty_restore()
            builtins.print() # newline
            builtins.print(*objects, sep=sep, end=end, file=file, flush=flush)
            self.tty_input()
        else:
            builtins.print(*objects, sep=sep, end=end, file=file, flush=flush)