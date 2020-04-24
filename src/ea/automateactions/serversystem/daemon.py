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

import sys
import os
import signal
import atexit
import time

class Daemon:
    """daemon"""
    def __init__(self, pidfile, name, stdout, stderr):
        """init class"""
        self._stdout = stdout
        self._stderr = stderr
        self._pidfile = pidfile
        self._procname = name

    def get_pidfile(self):
        """get pid from file"""
        pid = None
        
        # checking if the file exists on system
        if not os.path.exists(self._pidfile):
            return pid
            
        # read the pid
        with open(self._pidfile, 'r') as f:
            pid = int(f.read().strip())

        return pid
        
    def send_signal(self, pid, sig):
        """send signal"""
        try:
            os.kill(pid, sig)
        except Exception as e:
            return False
        return True

    def delete_pidfile(self):
        """delete pid file"""
        try:
            os.remove(self._pidfile)
        except Exception:
            pass
        
    def daemonize(self):
        """daemonize"""
        # do first fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #1 failed: %s" % e )
            sys.exit(1)
            
        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) # exit from second parent
        except OSError as e:
            sys.stderr.write("fork #2 failed: %s" % e )
            sys.exit(1)
            
        # Setup our signal handlers
        signal.signal(signal.SIGHUP, self.hup_handler)
        
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # 1 to select line buffering (only usable in text mode)
        sys.stdout = open(self._stdout, "a+", 1)
        sys.stderr = open(self._stderr, "a+", 1)
        
        # function called on exit
        atexit.register(self.delete_pidfile)

        # create pid file
        open(self._pidfile, 'w+').write('%s\n' % os.getpid())
        
    def is_running(self):
        """is running"""
        # get pid from file
        pid = self.get_pidfile()
        
        if pid is None:
            return False
            
        # checking if the process is running on system
        if not self.send_signal(pid,0):
            return False
        
        return True
      
    def status(self):
        """status of the daemon"""
        # process running ?
        pid = self.get_pidfile()
        
        running = True
        
        # process is not running
        if pid is None:
            running = False
        else:
            if not self.send_signal(pid,0):
                running = False
                # abnormal state, delete the file
                self.delete_pidfile()
        
        if running:
            message = "server is running\n"
        else:
            message = "server is not running\n"
        sys.stdout.write(message)
            
        return running
      
    def run(self):
        """run"""
        pass

    def send_hup(self):
        """send hup"""
        if not self.is_running():
            sys.stderr.write("send hup signal: server not started...\n")
            return
        
        pid = self.get_pidfile()
        if pid is None:
            sys.stderr.write("send hup signal: server not started...\n")
            return
            
        self.send_signal(pid, signal.SIGHUP)
       
    def hup_handler(self):
        """hup handler"""
        pass
        