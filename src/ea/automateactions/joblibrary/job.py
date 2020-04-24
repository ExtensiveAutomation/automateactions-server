
import threading 
import time

from ea.automateactions.joblibrary import jobhandler
from ea.automateactions.joblibrary import jobtracer

def find_snippet():
    t = threading.currentThread().getName()
    action = jobhandler.instance().get_snippet_by_thread(thread_name=t)
    return action
    
def log(message):
    """log message"""
    snippet = find_snippet()
    jobtracer.instance().log_snippet_info(ref=snippet.id,
                                         message=message)

def failure(message):
    """generate failure message"""
    snippet = find_snippet()
    snippet.failure(message=message)

def emit(msg):
    """emit user message"""
    snippet = find_snippet()
    snippet.emit(msg=msg)
        
def sleep(timeout):
    """sleep during xx seconds"""
    log(message="sleeping for %s sec" % timeout)
    time.sleep(timeout)
        