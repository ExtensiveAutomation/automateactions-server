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

import os
import sys

from ea.automateactions.serversystem import settings

class CliFunctions():
    """cli functions"""
    def __init__(self, coreserver):
        """init"""
        self.coreserver = coreserver
        
    def version(self):
        """Get version of the server"""
        v = settings.get(("version",))
        sys.stdout.write("Server version: %s\n" % v)
        
    def reload_configuration(self):
        """reload configuration"""
        self.coreserver.send_hup()
        
CliFncs = None

def instance():
    """instance"""
    return CliFncs
    
def version():
    """get server version"""
    return instance().version()
    
def reload_configuration():
    """reload configuration"""
    instance().reload_configuration()
    
def initialize(coreserver):
    """init"""
    global CliFncs
    CliFncs = CliFunctions(coreserver=coreserver)
        
def finalize():
    """finalize"""
    global CliFncs
    if CliFncs is not None:
        del CliFncs
        