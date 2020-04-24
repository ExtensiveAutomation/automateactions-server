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
import platform
import signal
import time
import traceback

from ea.automateactions.serversystem import daemon
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serversystem import scheduler
from ea.automateactions.serverengine import jobsmanager
from ea.automateactions.serverengine import workspacesmanager
from ea.automateactions.serverengine import globalsmanager
from ea.automateactions.serverengine import sessionsmanager
from ea.automateactions.serverengine import usersmanager
from ea.automateactions.servercontrol import cliserver
from ea.automateactions.servercontrol import restapi
from ea.automateactions.serverstorage import executionstorage
from ea.automateactions.serverstorage import actionstorage
from ea.automateactions.serverstorage import snippetstorage

n = os.path.normpath

settings.initialize()

path_backups = "%s/%s/" % (settings.get_app_path(),
                           settings.cfg['paths']['jobs-backups'])                   
path_results = '%s/%s/' % (settings.get_app_path(),
                          settings.cfg['paths']['jobs-executions']) 
path_workspaces = "%s/%s/" % (settings.get_app_path(),
                              settings.cfg['paths']['workspaces'])  
path_snippets = "%s/%%s/snippets/" % path_workspaces
path_actions = "%s/%%s/actions/" % path_workspaces                   
path_logs = "%s/%s/output.log" % (settings.get_app_path(),
                                  settings.cfg['paths']['server-logs'])
path_pid =  "%s/%s/server.pid" % (settings.get_app_path(),
                                    settings.cfg['paths']['server-logs'])                              
app_name = settings.cfg['name']

logger.initialize(log_file=path_logs,
                  level=settings.cfg['log']['level'],
                  max_size=settings.cfg['log']['max-size'],
                  nb_files=settings.cfg['log']['max-backup'])


class DaemonServer(daemon.Daemon):
    """daemon server"""
    def __init__(self):
        """init"""
        daemon.Daemon.__init__(self,
                               pidfile=n(path_pid),
                               name=app_name,
                               stdout=n(path_logs),
                               stderr=n(path_logs))

        
    def cleanup(self):
        """cleanup"""
        workspacesmanager.finalize()
        usersmanager.finalize()
        globalsmanager.finalize()
        sessionsmanager.finalize()
        
        scheduler.finalize()
        jobsmanager.finalize()
        actionstorage.finalize()
        snippetstorage.finalize()
        executionstorage.finalize()
        restapi.finalize()

        cliserver.finalize()
        
        settings.finalize()
        logger.finalize()

    def start(self):
        """start"""
        if self.is_running():
            logger.error("coreserver - server is already running")
            sys.exit(1)
            
        # run the server as daemon only for linux
        if platform.system() == "Linux":
            self.daemonize()
            
        logger.info("coreserver - starting up server...")
        
        try:
            cliserver.initialize(coreserver=self)
            logger.info("coreserver - cli [OK]")

            workspacesmanager.initialize(workspaces_path=n(path_workspaces))
            logger.info("coreserver - workspaces manager [OK]")
            
            usersmanager.initialize()
            logger.info("coreserver - users manager [OK]")
            
            globalsmanager.initialize(workspaces_path=n(path_workspaces))
            logger.info("coreserver - globals manager [OK]")
            
            sessionsmanager.initialize()
            logger.info("coreserver - sessions manager [OK]")
            
            scheduler.initialize()
            logger.info("coreserver - scheduler [OK]")
            
            jobsmanager.initialize(path_bckps=n(path_backups))
            logger.info("coreserver - jobs manager [OK]")
            
            executionstorage.initialize(repo_path=n(path_results))
            logger.info("coreserver - executions storage [OK]")
            
            actionstorage.initialize(repo_path=n(path_actions))
            logger.info("coreserver - actions storage [OK]")
            
            snippetstorage.initialize(repo_path=n(path_snippets))
            logger.info("coreserver - snippets storage [OK]")

            bind_ip = settings.cfg['network']['api-bind-ip']
            bind_port = settings.cfg['network']['api-bind-port']
            restapi.initialize(bind_addr=(bind_ip,bind_port))
            restapi.start()
            logger.info("coreserver - rest api server [OK]")
            
            jobsmanager.reload_jobs()
            logger.info("coreserver - jobs reloaded [OK]")
            
        except Exception:
            tb = traceback.format_exc()
            logger.error("coreserver - unable to start server: %s" % tb)
            self.cleanup()
            sys.exit(3)
            
        msg_success = "server successfully started!"
        logger.info(msg_success)
        if platform.system() == "Windows":
            print(msg_success)

        self.run()
        
    def stop(self):
        """stop"""
        if self.is_running():
            pid = self.get_pidfile()
            try:
                while True:
                    os.kill(pid,signal.SIGTERM)
                    time.sleep(0.5)
            except OSError:
                pass
                
            self.delete_pidfile()

        sys.exit(0)
            
    def run(self):
        """Running in loop"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
            self.stop()

    def hup_handler(self, signum, frame):
        """
        Hup handler
        """
        logger.info('coreserver - reloading configuration...')

        # reload settings ini
        settings.finalize()
        settings.initialize()

        # reconfigure the level of log message
        level = settings.cfg['log']['level']
        logger.set_level(level=level)

        # reload cache
        UsersManager.instance().loadCache()

        logger.info('coreserver - configuration reloaded!')

DaemonSvr = None  # singleton


def instance():
    """Returns the singleton"""
    return DaemonSvr

def start():
    """Start the server"""
    instance().start()

def stop():
    """Stop the server"""
    instance().cleanup()
    instance().stop()

def status():
    """Return the status of the server"""
    instance().status()

def initialize():
    """Instance creation"""
    global DaemonSvr
    DaemonSvr = DaemonServer()