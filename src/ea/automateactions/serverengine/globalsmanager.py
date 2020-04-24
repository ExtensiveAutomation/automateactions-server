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
import time
import yaml

from ea.automateactions.serverengine import constant
from ea.automateactions.serversystem import settings
from ea.automateactions.serversystem import logger

n = os.path.normpath

class GlobalsManager:
    """globlas environment class"""
    def __init__(self, workspaces_path):
        """class init"""
        self.workspaces_path = workspaces_path

    def get_entries(self, workspace):  
        """get all entries according to the project id provided"""
        logger.debug("globals - get entries")

        env_file = '%s/%s/globals.yml' % (self.workspaces_path, workspace)

        entries = ""
        try:
            with open( n(env_file) ) as f:
                entries = f.read() 
        except FileNotFoundError:
            logger.error("globals - globals file missing for workspace=%s" % workspace)

        return (constant.OK, entries)

    def save_entries(self, content, workspace):
        """save entries"""
        logger.debug("globals - save entries")

        env_file = '%s/%s/globals.yml' % (self.workspaces_path, workspace)

        try:
            yaml.safe_load(content)
        except Exception as e:
            error_str = "invalid yaml - %s" % e
            logger.error('globals - %s' % error_str)
            return (constant.ERROR, error_str)

        with open( n(env_file), "w") as f:
            f.write(content)

        return (constant.OK, "success")

GblsMngr = None

def get_entries(workspace):
    """get global environment"""
    return instance().get_entries(workspace=workspace)

def saves_entries(content, workspace):
    """save new globals environment"""
    return instance().save_entries(content=content,
                                   workspace=workspace)

def instance():
    """returns the singleton"""
    global GblsMngr
    return GblsMngr

def initialize(workspaces_path):
    """instance creation"""
    global GblsMngr
    GblsMngr= GlobalsManager(workspaces_path=workspaces_path)

def finalize():
    """destruction of the singleton"""
    global GblsMngr
    if GblsMngr:
        del GblsMngr
        GblsMngr = None
