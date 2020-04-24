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

import threading

from pycnic.core import WSGI

from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIRequestHandler

from ea.automateactions.servercontrol import apiresources
from ea.automateactions.serversystem import logger

class WSGIRequestHandlerLogging(WSGIRequestHandler):
    """wsgi request handler logging"""
    def log_message(self, format, *args):
        """log message"""
        try:
            logger.debug("restapi - %s %s %s" % args)
        except BaseException:
            print(args)

uuid_regex = r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}" \
             r"\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}" \
             r"\-[0-9a-fA-F]{12}"
class WebServices(WSGI):
    headers = [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "*"),
        ("Access-Control-Allow-Headers", "X-Requested-With, "
                                         "Content-Type, "
                                         "Origin, "
                                         "Authorization, "
                                         "Accept, "
                                         "Client-Security-Token, "
                                         "Accept-Encoding")
    ]
    logger = None
    routes = [
        ('/v1/session', apiresources.SessionHandler()),
        ('/v1/users', apiresources.UserHandler()),
        ('/v1/users/(.*)/password', apiresources.UserPasswordHandler()),
        ('/v1/users/(.*)', apiresources.UserHandler()),
        ('/v1/globals', apiresources.GlobalsHandler()),
        ('/v1/globals/(.*)', apiresources.GlobalsHandler()),
        ('/v1/workspaces', apiresources.WorkspacesHandler()),
        ('/v1/workspaces/(.*)' , apiresources.WorkspacesHandler()),
        ('/v1/jobs', apiresources.JobsHandler()),
        ('/v1/jobs/(%s)' % uuid_regex, apiresources.JobsHandler()),
        ('/v1/executions', apiresources.ExecutionsHandler()),
        ('/v1/executions/(%s)' % uuid_regex, apiresources.ExecutionsHandler()),
        ('/v1/actions', apiresources.ActionsHandler()),
        ('/v1/actions/(.*)', apiresources.ActionsHandler()),
        ('/v1/snippets', apiresources.SnippetsHandler()),
        ('/v1/snippets/(.*)', apiresources.SnippetsHandler()),
    ]


class RestServer(threading.Thread):
    def __init__(self, bind_addr):
        """init"""
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()

        self.httpd = make_server(host=bind_addr[0],
                                 port=bind_addr[1],
                                 app=WebServices,
                                 handler_class=WSGIRequestHandlerLogging
                                 )

    def run(self):
        """
        Run server
        """
        logger.debug("restapi - server started")
        try:
            while not self.stop_event.isSet():
                self.httpd.serve_forever()
        except Exception as e:
            logger.error("restapi - exception: " + str(e))
        logger.debug("restapi - server stopped")

    def stop(self):
        """
        Stop server
        """
        self.stop_event.set()
        self.httpd.shutdown()
        self.join()


RestSvr = None  # singleton

def instance():
    """Returns the singleton of the rest server"""
    return RestSvr

def start():
    """start"""
    instance().start()
    
def initialize(bind_addr):
    """Rest server instance creation"""
    global RestSvr
    RestSvr = RestServer(bind_addr=bind_addr)

def finalize():
    """Destruction of the singleton"""
    global RestSvr
    if RestSvr is not None:
        RestSvr.stop()
        RestSvr = None