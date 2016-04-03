import threading
from functools import wraps
import functools

def error(num):
	if num == 1:
		return "Error: Params too few."
	if num == 2:
		return "Error: Internet Issue server returns invalid number of params try again."
	if num == 3:
		return "Error: Internal Error."



def delay(delay=0.):
    """
    Decorator delaying the execution of a function for a while.
    """
    def wrap(f):
        @wraps(f)
        def delayed(*args, **kwargs):
            timer = threading.Timer(delay, f, args=args, kwargs=kwargs)
            timer.start()
        return delayed
    return wrap
