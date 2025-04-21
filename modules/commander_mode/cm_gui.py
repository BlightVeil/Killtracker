

yourwindow.protocol("WM_DELETE_WINDOW", whatever)

def whatever():
    yourwindow.destroy()
    stop heartbeat thread
    # Replace this with your own event for example:
    print("oi don't press that button")