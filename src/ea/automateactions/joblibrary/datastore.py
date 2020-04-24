import threading
import re

from ea.automateactions.joblibrary import jobhandler

class JobCache():
    """job cache"""
    def __init__(self):
        """init class"""
        self._cache = {}

    def capture(self, data, regexp):
        """capture data  and save it in cache"""
        matched = re.search(regexp, data, re.S)
        if matched is not None:
            if len(matched.groups()):
                self._cache.update(matched.groupdict())
     
    def set(self, name, data):
        """set data in the cache"""
        self._cache.update({name: data})
        
    def all(self):
        """return cache content"""
        return self._cache
        
    def get(self, name, default=None):
        """get one value from the cache"""
        return self._cache.get(name,default)
        
    def delete(self, name):
        """delete one key/value"""
        self._cache.pop(name, None)
        
    def reset(self):
        """reset the cache"""
        del self._cache
        self._cache = {}
        
JobCacheIns = None

def instance():
    """Return the instance"""
    global JobCacheIns
    if JobCacheIns:
        return JobCacheIns

def initialize():
    """init"""
    global JobCacheIns
    JobCacheIns = JobCache()


def find_snippet():
    t = threading.currentThread().getName()
    snippet = jobhandler.instance().get_snippet_by_thread(thread_name=t)
    return snippet

def subtitute(current_value, regex, new_value):
    matched = re.findall(regex, current_value)

    for el in matched:
        pattern, keys = el
        keys_list = keys.split(".")

        nv = new_value(keys_list[0])
        for k in keys_list[1:]:
            if isinstance(nv, dict):
                nv = nv.get(k, None)

        if pattern == current_value:
            current_value = nv
            break

        current_value = current_value.replace(pattern, "%s" % nv, 1)
    return current_value

class Globals:
    def get(self, name):
        """return variable value"""
        return jobhandler.instance().globals.get(name, None)

class Variables:
    def get(self, name):
        """return variable value"""
        snippet = find_snippet()
        v = snippet.get_variable(var_name=name)

        if isinstance(v, str):
            settings_regex = r"(?P<settings>\$\{\{globals\.(?P<settings_keys>[\w-]+(?:\.[\w-]+)*)\}\})"
            v = subtitute(v, settings_regex, Globals().get )

        if isinstance(v, str):
            cache_regex = r"(?P<cache>\$\{\{cache\.(?P<cache_keys>[\w-]+(?:\.[\w-]+)*)\}\})"
            v = subtitute(v, cache_regex, instance().get )
        return v

variables  = Variables().get
globals  = Globals().get

def capture(data, regexp):
    """capture"""
    instance().capture(data, regexp)
    
def save(name, data):
    """set"""
    instance().set(name=name, data=data)
    
def cache(name, default=None):
    """get"""
    return instance().get(name=name, default=default)
    
def all():
    """all"""
    return instance().all()
    
def delete(name):
    """delete"""
    instance().delete(name=name)
    
def reset():
    """reset"""
    instance().reset()