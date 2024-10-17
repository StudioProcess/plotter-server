import asyncio
import sys
import termios
import tty
import builtins
import io

# async prompt for a single keystroke
class AsyncPrompt:
    def __init__(self):
        self.echo = True
        self.echo_end = '\n'
        self.waiting_for_input = False
        self.queue = asyncio.Queue()
        asyncio.get_running_loop().add_reader(sys.stdin, self.on_input)
    
    def __del__(self):
        # restore tty if object goes away
        if self.waiting_for_input:
            self.tty_restore()
    
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
            sys.stdin.seek(0, io.SEEK_END) # disard rest of input (by seeking to end of stream)
            self.tty_restore()
            if ord(key) == 3: # catch Control-C
                raise KeyboardInterrupt()
            if self.echo:
                if ord(key) == 27:
                    print('^[', end=self.echo_end) # Don't echo ESC as it is, this would start an escape sequence in the terminal
                else:
                    print(key, end=self.echo_end) # echo the input character (with newline)
            self.queue.put_nowait(key)
            self.waiting_for_input = False
        else:
            sys.stdin.readline() # discard input
    
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