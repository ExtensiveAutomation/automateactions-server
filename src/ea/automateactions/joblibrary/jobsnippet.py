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

from ea.automateactions.serverengine import constant
from ea.automateactions.joblibrary import jobtracer
from ea.automateactions.joblibrary import jobhandler

class FailureException(Exception):
    pass

class Snippet:
    """snippet class"""
    def __init__(self, id, name, when={}, vars={}, vars_sub={}):
        """class init"""
        self._retcode = constant.RETCODE_PASS
        self.id = id
        self._thread = None
        self.name = name
        self.state = constant.SNIPPET_CREATED
        self.creation_time = time.time()
        self.vars = vars
        self.vars_sub = vars_sub

        self.links_in = []
        self.links_out = []

        self.init_links(when=when)
        self.need_to_start()

    def get_variable(self, var_name):
        """return variable value"""
        if var_name not in self.vars:
            return None

        return self.vars[var_name]

    def init_links(self, when):
        """init links"""
        # init incoming links
        for (k, v) in when.items():
            d = {}
            d["name"] = k
            d["msg"] = v
            d["enable"] = False
            self.links_in.append(d)
            
        # init outgoing links on others snippets
        for (k, v) in when.items():
            for act in jobhandler.get_snippets():
                if act.name == k:
                    d = {}
                    d["name"] = self.name
                    d["msg"] = v
                    act.links_out.append(d)

    def cancel(self):
        """cancel the snippet"""
        self.state = constant.SNIPPET_TERMINATED
        
        # cancel the other linked snippets
        for l in self.links_out:
            act = jobhandler.get_snippet(name=l["name"])
            act.cancel()
            
    def trigger(self, msg, cancel_all=True):
        """trigger other snippets"""
        for l in self.links_out:
            # find the snippet in the job handler with the name
            act = jobhandler.get_snippet(name=l["name"])
            
            # same message on the snippet ?
            if l["msg"] == msg:
                # updating starting conditions
                act.update_conds(name=self.name,
                                 msg=msg)
                # need to start the snippets? 
                act.need_to_start()
            
            else:
                if cancel_all:
                    act.cancel()
                    
    def update_conds(self, name, msg):
        """update starting conditions"""
        for l in self.links_in:
            if l["name"] == name and l["msg"] == msg:
                # message received from previous snippet
                # activates the link
                l["enable"] = True
        
    def need_to_start(self):
        """check the start condition"""
        # the snippet is already terminated, do nothing
        # in this case
        if self.state == constant.SNIPPET_TERMINATED:
            return
            
        # no previous snippets exists
        # this snippet can be started right now 
        if not len(self.links_in):
            self.notify(msg=constant.NOTIFY_START)
        
        # otherwise, we need to wait the 
        # activation of each incoming links
        else:
            conds_meet = True
            for l in self.links_in:
                if l["enable"] == False:
                    conds_meet = False
                    break
                
            if conds_meet:
                self.notify(msg=constant.NOTIFY_START)

    def set_thread(self, t):
        """set thread"""
        self._thread = t

    def start(self):
        """start the thread"""
        # the snippet is already terminated, do nothing
        # in this case
        if self.state == constant.SNIPPET_TERMINATED:
            return
            
        # start the snippet in a thread
        self.state = constant.SNIPPET_STARTED
        self._thread.start()
     
    def notify(self, msg):
        """notify job handler"""
        event = { "snippet": self, "msg": msg}
        jobhandler.enqueue_event( event )
        
    def get_retcode(self):
        """return the result of the snippet"""
        return self._retcode
  
    def error(self, message):
        """log error message and stop the snippet"""
        self._retcode = constant.RETCODE_ERROR
        jobtracer.instance().log_snippet_error(ref=self.id, message=message)
        
        self.state = constant.SNIPPET_TERMINATED
        self.notify(msg=constant.NOTIFY_FAILURE)

    def failure(self, message):
        """generate failure message"""
        raise FailureException(message)

    def emit(self, msg):
        """emit user message"""
        self.trigger(msg=msg, cancel_all=False)

    def done(self):
        """emit done signal"""
        if self.state == constant.SNIPPET_TERMINATED:
            return
            
        self.state = constant.SNIPPET_TERMINATED
        self.notify(msg=constant.NOTIFY_DONE)
            
    def begin(self, description):
        """log begin message"""
        jobtracer.instance().log_snippet_started(ref=self.id,
                                                name=description)
     
    def ending(self, duration):
        """log ending message"""
        result = constant.RETCODE_LIST[self._retcode]
        jobtracer.instance().log_snippet_stopped(ref=self.id,
                                                result=result,
                                                duration=duration)
