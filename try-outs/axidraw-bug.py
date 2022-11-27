from pyaxidraw import axidraw

ad = axidraw.AxiDraw()
ad.interactive()

connected = ad.connect()
if not connected: exit()

ad.moveto(1, 1)                 # Pen-up move to (1 inch, 1 inch)
ad.lineto(2, 1)                 # Pen-down move, to (2 inch, 1 inch)
ad.moveto(0, 0)

ad.penup()
ad.disconnect()





def moveto(x, y):
    ad.penup()
    ad.goto(x, y)

def lineto(x, y):
    ad.pendown()
    ad.goto(x, y)


# moveto(1, 1)
# lineto(2, 1)
# moveto(0, 0)

# ad.moveto(W/2, H/2)
# time.sleep(1)

# an X
# moveto(-R + W/2,  R + H/2)
# lineto( R + W/2, -R + H/2)
# moveto(-R + W/2, -R + H/2)
# lineto( R + W/2,  R + H/2)
