import random, time
try:
    with open('time','r') as f:
        timer = float(f.read())
except IOError:
    timer = time.time()
    with open('time','w') as f:            
        f.write(str(timer))
    
#    print timer
duration = 10

def level(ch):
    if ch == 2:        
        if time.time() < timer + duration:
            return 1.00
        else:
            return 0.01
    elif ch == 1:
        if time.time() < timer + duration:
            return 0.01
        else:
            return 1.00
    else:
        return 1.0
