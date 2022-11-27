from pyaxidraw import axidraw
import time

# Customized AxiDraw, that adds a disable_motors() function
# Can be used in interactive mode (when connected)
from axidrawinternal.plot_utils_import import from_dependency_import # plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')
class AxiDraw(axidraw.AxiDraw):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def disable_motors(self):
        ebb_motion.sendDisableMotors(self.plot_status.port, False)

W=420
H=297
R=15


def test():
    ad = axidraw.AxiDraw()
    ad.interactive()
    
    ad.options.model = 2 # AxiDraw V3/A3 or SE/A3. See: https://axidraw.com/doc/py_api/#model
    ad.options.units = 2 # mm. See: https://axidraw.com/doc/py_api/#units
    
    connected = ad.connect()
    if not connected:
        print('No connection')
        return()
    print('Connected to AxiDraw')
    
    # configureable options
    print('ad.options')
    print(ad.options)
    
    # advanced params
    print('ad.params')
    print(dir(ad.params))
    
    
    print('ad.errors')
    print(dir(ad.errors))

    ad.options.units = 0
    ad.update()
    ad.moveto(1, 1)                 # Pen-up move to (1 inch, 1 inch)
    ad.lineto(2, 1)                 # Pen-down move, to (2 inch, 1 inch)
    ad.moveto(0, 0)
    
    ad.penup()
    ad.goto(0, 0)
    ad.disconnect()

    # ad.moveto(W/2, H/2)
    # time.sleep(1)
    
    # an X
    # ad.moveto(-R + W/2,  R + H/2)
    # ad.lineto( R + W/2, -R + H/2)
    # ad.moveto(-R + W/2, -R + H/2)
    # ad.lineto( R + W/2,  R + H/2)

# Raise pen and disable XY stepper motors
def align():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = 'align' # A setup mode: Raise pen, disable XY stepper motors
    ad.plot_run()

# Cycle the pen down and back up
def cycle():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = "cycle" # A setup mode: Lower and then raise the pen
    ad.plot_run()

# Report system information
def sysinfo():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = "sysinfo"
    ad.plot_run()


def version():
    ad = axidraw.AxiDraw()
    ad.plot_setup()
    ad.options.mode = "version"
    ad.plot_run()
    

def test_disable_motors():
    ad = AxiDraw()
    ad.interactive()
    ad.connect()
    ad.penup()
    ad.disable_motors()
    # ad.enable_motors()
    ad.disconnect()
    
def test_enable_motors():
    ad = AxiDraw()
    ad.interactive()
    ad.connect()
    ad.penup()
    # ad.enable_motors() # no need to call, done by connect
    ad.disconnect()



svg1 = '''<!-- Created with tg-plot (v 1) at 2022-11-10T16:10:03.360Z -->
<svg xmlns="http://www.w3.org/2000/svg" 
     width="420mm"
     height="297mm"
     viewBox="-210 -148.5 420 297"
     stroke="black" fill="none" stroke-linecap="round">
    <path d="M -141.075 -141.075 L 141.075 -141.075 141.075 141.075 -141.07499999999996 141.075 -141.07499999999996 -141.07499999999996 M 0 141.075 L 0 -141.075 M -141.075 0 L 141.075 0 M 0 -141.075 L 19.951017831178437 -121.12398216882154 M 0 -141.075 L -19.951017831178433 -121.12398216882154" />
</svg>'''
svg2 = '''<!-- Created with tg-plot (v 1) at 2022-11-10T16:11:07.211Z -->
<svg xmlns="http://www.w3.org/2000/svg" 
     width="420mm"
     height="297mm"
     viewBox="-210 -148.5 420 297"
     stroke="black" fill="none" stroke-linecap="round">
    <path d="M -199.49999999999997 -99.74999999999999 L 199.49999999999997 -99.74999999999999 199.49999999999997 99.74999999999999 -199.49999999999997 99.74999999999999 -199.49999999999994 -99.74999999999994 M 0 99.74999999999999 L 0 -99.74999999999999 M -199.49999999999997 0 L 199.49999999999997 0 M 0 -99.74999999999999 L 21.160170427007433 -78.58982957299256 M 0 -99.74999999999999 L -21.16017042700743 -78.58982957299256" />
</svg>'''
svg3 = '''<!-- Created with tg-plot (v 1) at 2022-11-10T16:11:30.945Z -->
<svg xmlns="http://www.w3.org/2000/svg" 
     width="420mm"
     height="297mm"
     viewBox="-210 -148.5 420 297"
     stroke="black" fill="none" stroke-linecap="round">
    <path d="M -70.5375 -141.075 L 70.5375 -141.075 70.5375 141.075 -70.53749999999998 141.075 -70.53749999999995 -141.07499999999996 M 0 141.075 L 0 -141.075 M -70.5375 0 L 70.5375 0 M 0 -141.075 L 14.963263373383827 -126.11173662661616 M 0 -141.075 L -14.963263373383825 -126.11173662661616" />
</svg>'''

def plot_svg_text(text):
    ad = axidraw.AxiDraw()
    ad.plot_setup(text)
    ad.options.model = 2
    ad.options.reordering = 4
    ad.options.speed_pendown = 110
    ad.options.speed_penup = 110
    ad.options.accel = 100
    ad.options.pen_rate_lower = 100
    ad.options.pen_rate_raise = 100
    
    ad.plot_run()
    print('done plog_svg_text')

if __name__ == '__main__':
    # test()
    # align()
    # cycle()
    # test_disable_motors()
    # test_enable_motors()
    # version()
    
    plot_svg_text(svg1)
