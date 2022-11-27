import curses
from curses.textpad import Textbox, rectangle

message = ''

# print(dir(curses))
# exit()


def main(stdscr):
    stdscr.addstr(0, 0, "Enter IM message: (hit Ctrl-G to send)")

    editwin = curses.newwin(5,30, 2,1)
    rectangle(stdscr, 1,0, 1+5+1, 1+30+1)
    stdscr.refresh()

    box = Textbox(editwin)
    
    def edit_validator(key):
        if key == 10: # Enter
            return 7 # Control-G
        if key == 127: # Backspace
            box.do_command(2) # Control-B (Left)
            box.do_command(4) # Control-D (Delete)
            return
        # for ch in str(key):
        #     box.do_command(ch)
        # box.do_command(' ')
        return key
    
    # Let the user edit until Ctrl-G is struck.
    box.edit(edit_validator)

    # Get resulting contents
    global message
    message = box.gather().strip()


curses.wrapper(main)

print(message)

# Control-A = 1
# Control-B = 2
# Control-D = 4
# Control-E = 101
# Control-F = 6
# Control-G = 7
# Control-H = 263
# Control-J = 10
# Control-K = 11
# Control-L = 12
# Control-N = 14
# Control-O = -
# Control-P = 16