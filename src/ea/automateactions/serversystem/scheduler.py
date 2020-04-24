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
import heapq

from ea.automateactions.serverengine import constant
from ea.automateactions.serversystem import logger

class SchedulerEvent():
    """Scheduler event"""
    def __init__(self, ref, callback, timestamp, args, kwargs):
        """class event"""
        self.ref = ref
        self.callback = callback
        self.timestamp = timestamp
        self.args = args
        self.kwargs = kwargs
    def __lt__(self, other):
        """less-than comparison"""
        return self.timestamp < other.timestamp
        
class SchedulerThread(threading.Thread):
    """scheduler thread with queue support"""
    def __init__(self):
        """scheduler class"""
        threading.Thread.__init__(self)
        self.event = threading.Event()
        self.mutex = threading.RLock()
        self.queue = []
        self.running = True
        self.expire = None
        
    def add_event(self, ref, timestamp, callback, *args, **kwargs):
        """add event in the queue"""
        self.mutex.acquire()
        success = constant.OK
        new_event = None
        try:  
            logger.debug("scheduler - adding event %s" % timestamp)
            self.expire = timestamp - time.time()
            
            # create a new event and put it in the queue
            new_event = SchedulerEvent(ref, callback, 
                                       timestamp,
                                       args,
                                       kwargs)
            heapq.heappush(self.queue, new_event )
            
            # activate the event
            self.event.set()
        except Exception as e:
            logger.error("scheduler - exception while "
                         "adding event %s" % e)
            success = constant.ERROR
        self.mutex.release()
        return (success, new_event)
        
    def remove_event(self, event):
        """remove event from queue"""
        self.mutex.acquire()
        try:
            if self.queue:
                logger.debug("scheduler - remove event")
                self.queue.remove(event)
                heapq.heapify(self.queue)
                del event
        except Exception as e:
            logger.error("scheduler - exception while "
                         "removing event %s: %s" % (event.ref, e) )
        self.mutex.release()
        
    def update_event(self, event, timestamp):
        """update event timestamp"""
        self.mutex.acquire()
        try:
            if self.queue:
                logging.info("update event")
                # remove event from the queue
                self.queue.remove(event)
                heapq.heapify(self.queue)

                # update the timestamp of the event
                event.timestamp = timestamp
                heapq.heappush(self.queue, event)
                
                self.event.set()
        except Exception as e:
            logger.error("scheduler - exception while "
                         "updating event %s" % event.ref)
        self.mutex.release()

    def stop(self):
        """stop the scheduler"""
        self.mutex.acquire()
        logger.debug("scheduler - stopping scheduler")
        self.running = False
        self.event.set()
        self.mutex.release()
        
    def run(self):
        """run thread loop"""
        q = self.queue
        while self.running:
            # block until the event is set or timeout occurs
            self.event.wait(self.expire)
            if self.running:
                self.mutex.acquire()
                if q:
                    # time to run event ?
                    if (time.time() - q[0].timestamp) < 0:
                        # too early, update next wake up
                        self.expire = q[0].timestamp - time.time()
                        self.event.clear()
                        
                    else:
                        logger.debug("scheduler - running event %s" % q[0].ref)
                        try:
                            t = threading.Thread(target=q[0].callback,
                                                 args=q[0].args,
                                                 kwargs=q[0].kwargs)
                            t.start()
                        except Exception as e:
                            logger.error("scheduler - exception while "
                                         "executing event %s: %s" % (q[0].ref, e))
                        
                        # remove event from queue
                        heapq.heappop(q)
                        
                        # queue is empty ?
                        if q:
                            # update next wake up
                            self.expire = q[0].timestamp - time.time()
                            self.event.clear()
                        else:
                            # no more event, go to sleep
                            self.expire=None
                            self.event.clear()

                self.mutex.release()

Sched = None

def initialize():
    """init the scheduler"""
    global Sched
    if Sched is None:
        Sched = SchedulerThread()
        Sched.start()
        
def finalize():
    """stop the scheduler"""
    global Sched
    if Sched:
        Sched.stop()
        Sched.join()
        del Sched
        
def instance():
    """scheduler instance"""
    global Sched
    return Sched
    
def add_event(ref, timestamp, callback, *args, **kwargs):
    """add event"""
    return instance().add_event(ref, timestamp, callback, *args, **kwargs)
    
def remove_event(event):
    """remove event"""
    instance().remove_event(event)
    
def update_event(event):
    """update event"""
    instance().update_event(event)