#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -------------------------------------------------------------------
# Copyright (c) 2010-2020 Denis Machard
# This file is part of the extensive automation project
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA
# -------------------------------------------------------------------

import time
import threading
import queue

from ea.automateactions.joblibrary import jobtracer
from ea.automateactions.serverengine import constant

class JobHandler(threading.Thread):
    """job handler library"""
    def __init__(self, globals):
        """class init"""
        threading.Thread.__init__(self)
        self.q =  queue.Queue()
        self.e = threading.Event()
        self.r = True

        self.globals = globals

        self.ret_code = constant.RETCODE_PASS

        self.snippets_list = []
    
    def get_snippets(self):
        """return snippets list"""
        return self.snippets_list
    
    def get_snippet(self, name):
        """get snippet instance"""
        ret = None
        for s in self.snippets_list:
            if s.name == name:
                ret = s
                break
        return ret
        
    def get_snippet_by_thread(self, thread_name):
        """get snippet by thread"""
        for s in self.snippets_list:
            if s._thread.name == thread_name:
                return s
            
    def get_retcode(self):
        """get final return code"""
        if self.ret_code == constant.RETCODE_ERROR:
            return self.ret_code

        for act in self.snippets_list:
            if act.get_retcode() == constant.RETCODE_ERROR:
                self.ret_code = act.get_retcode()
                break
                
        return self.ret_code
        
    def set_error(self):
        """set return code to the value error"""
        self.ret_code = constant.RETCODE_ERROR
        
    def register(self, snippet, cb):
        """register snippet"""
        t = threading.Thread(target=cb, args=(snippet,))
        snippet.set_thread(t=t)
        
        self.snippets_list.append( snippet )

    def stop(self):
        """stop thread"""
        self.r = False

    def enqueue_event(self, snippet):
        """add event in queue"""
        self.q.put(snippet)
        self.e.set()
        
    def run(self):
        """run thread"""
        while self.r:
            self.e.wait()
            if self.r:
                while not self.q.empty():
                    # read the received event
                    event = self.q.get(False)
                    
                    # start snippet ?
                    if event["msg"] == constant.NOTIFY_START:
                        event["snippet"].start()

                    else:
                        event["snippet"].trigger(msg=event["msg"])
                        
                # no more snippets to execute ?
                score = 0
                for snippet in self.snippets_list:
                    score += snippet.state

                if score == len(self.snippets_list) * 2:
                    self.stop()
                    
                self.e.clear()
        self.e.clear()
        
JobHdl = None

def enqueue_event(snippet):
    """enqueue snippet event"""
    instance().enqueue_event(snippet=snippet)
    
def register(snippet, cb):
    """register snippet"""
    instance().register(snippet, cb)
 
def get_snippet(name):
    """get snippet instance"""
    return instance().get_snippet(name=name)
    
def get_retcode():
    """get return code"""
    return instance().get_retcode()
    
def error():
    """set error"""
    instance().set_error()

def get_snippets():
    """return snippets list"""
    return instance().get_snippets()

def instance():
    """Return the instance"""
    global JobHdl
    if JobHdl:
        return JobHdl

def finalize():
    """finalize"""
    instance().join()
    
def initialize(globals):
    """init"""
    global JobHdl
    JobHdl = JobHandler(globals=globals)
