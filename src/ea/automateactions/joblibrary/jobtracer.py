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

class JobTracer(object):
    """job tracer"""
    def __init__(self, result_path):
        """class init"""
        self.fd_logs = open('%s/job.log' % result_path, 'a+', 1)

    def get_path_log(self):
        """get path logs"""
        return self.fd_logs.name
        
    def get_timestamp(self):
        """Return a timestamp"""
        return time.strftime("%H:%M:%S", time.localtime(time.time())) + \
            ".%4.4d" % int((time.time() * 10000) % 10000)
        
    def close(self):
        """close"""
        self.fd_logs.close()
        
    def trace(self, value):
        """savetrace"""
        raw_line = "%s %s\n" % (self.get_timestamp(),
                                value)
        self.fd_logs.write(raw_line)
        
    def log_job_started(self):
        """job started"""
        self.trace(value="0 job-started")
        
    def log_job_stopped(self, result, duration):
        """job stopped"""
        self.trace(value="0 job-stopped %s %.3f" % (result,
                                                    duration) )
        self.fd_logs.close()
        
    def log_job_error(self, message):
        """job error"""
        self.trace(value="0 job-error %s" % message)
        
    def log_job_info(self, message):
        """job info"""
        self.trace(value="0 job-log %s" % message)
        
    def log_snippet_error(self, ref, message):
        """sniipet error"""
        self.trace(value="%s snippet-error %s" % (ref,message) )
        
    def log_snippet_info(self, ref, message):
        """snippet info"""
        self.trace(value="%s snippet-log %s" % (ref,message) )

    def log_snippet_started(self, ref, name):
        """snippet started"""
        self.trace(value="%s snippet-begin %s" % (ref, name) )
        
    def log_snippet_stopped(self, ref, result, duration):
        """snippet stopped"""
        self.trace(value="%s snippet-ending %s %.3f" % (ref,
                                                    result,
                                                    duration))

class StdWriter():
    """stdout/stderr overwrite"""
    def __init__(self, mode_err=False):
        """init class"""
        self.mode_err=mode_err
        
    def write(self, text):
        """write"""
        if text == "\n":
            return
        if self.mode_err:
            instance().log_job_error(message=text)
        else:
            instance().log_job_info(message=text)
            
    def flush(self):
        """flush"""
        instance().fd_logs.flush()
        
    def close(self):
        """close"""
        instance().fd_logs.flush()
        
    def fileno(self):
        """fileno"""
        return instance().fd_logs.fileno()
 
TracerIns = None

def get_path_log():
    """get path logs"""
    return instance().get_path_log()
    
def instance():
    """Return the instance"""
    global TracerIns
    if TracerIns is not None:
        return TracerIns

def finalize():
    """finalize"""
    global TracerIns
    if TracerIns is not None:
        TracerIns.close()
        del TracerIns
        
def initialize(result_path):
    """init"""
    global TracerIns
    TracerIns = JobTracer(result_path=result_path)
