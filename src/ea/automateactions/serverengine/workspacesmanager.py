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
import shutil
import yaml

from ea.automateactions.serverengine import constant
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings

n = os.path.normpath

class WorkspacesManager:
    """workspaces manager"""
    def __init__(self, workspaces_path):
        """class init"""
        self.workspaces_path = workspaces_path
        self.cache = []
        
        self.load_workspaces()
        self.tree_init()

    def save_workspaces(self):
        """"save workspaces to file"""
        # checking if the file exists
        wrks_file = '%s/data/workspaces.yml' % (settings.get_app_path())
        if not os.path.isfile(n(wrks_file)):
            raise Exception("yaml workspaces file doesn't exist in data/")

        try:
            wrks_str = yaml.safe_dump(self.cache)
        except Exception as e:
            raise Exception("dump workspaces config error: %s" % e)

        with open(wrks_file, 'w') as fd:
            fd.write(wrks_str)

    def load_workspaces(self):
        """load workspaces"""
        wrk_file = '%s/data/workspaces.yml' % (settings.get_app_path())
        if not os.path.isfile(n(wrk_file)):
            raise Exception("yaml workspaces file doesn't exist in data/")

        # load yaml
        with open(wrk_file, 'r') as fd:
            wrks_str = fd.read()

        try:
            self.cache = yaml.safe_load(wrks_str)
        except Exception as e:
            raise Exception("bad yaml workspaces file provided: %s" % e)

        logger.debug("workspacesmanager - workspaces cache "
                     "nb items: %s" % len(self.cache["workspaces"]) )

    def tree_init(self):
        """init tree folders"""
        logger.debug("workspacesmanager - creating folders if missing ")

        for w in self.cache["workspaces"]:
            # create the main folder if missing
            wrk_path = "%s/%s" % (self.workspaces_path, w)
            if not os.path.exists(n(wrk_path)):
                os.mkdir(n(wrk_path))

                snippets_path = "%s/snippets/" % wrk_path
                actions_path = "%s/actions/" % wrk_path
                os.mkdir( n(snippets_path) )
                os.mkdir( n(actions_path) )

    def search_workspace(self, name):
        """get workspace from cache by name"""
        logger.debug("workspacemanager - search if name=%s exists)" % name)
        if name in self.cache["workspaces"]:
            return name
        return None
            
    def get_workspaces(self):
        """get all workspaces"""
        logger.debug("workspacesmanager - get list")
        return (constant.OK, self.cache["workspaces"])

    def add_workspace(self, name):
        """create a new workspace"""
        logger.debug("workspacesmanager - add workspace name=%s" % name)

        wrk_path = "%s/%s" % (self.workspaces_path, name)
        if os.path.exists(n(wrk_path)):
            return (constant.ERROR, "workspace name must be unique")

        # checking in cache if the name is free
        if self.search_workspace(name=name):
            return (constant.ALREADY_EXISTS, "workspace name must be unique in cache")

        # create main workspace folder
        os.mkdir( n(wrk_path) )

        # create sub folders 
        snippets_path = "%s/snippets/" % wrk_path
        actions_path = "%s/actions/" % wrk_path
        os.mkdir( n(snippets_path) )
        os.mkdir( n(actions_path) )

        # add workspaces in the cache and save it
        self.cache["workspaces"].append( name )

        # save cache to file
        self.save_workspaces()

        return (constant.OK, "success" )
        
    def delete_workspace(self, name):
        """delete project"""
        logger.debug("projectsmanager - delete workspace name=%s" % name)
        
        # checking in cache if the workspace exists
        if self.search_workspace(name=name) is None:
            return (constant.NOT_FOUND, "workspace not found")

        # remove folder
        wrk_path = "%s/%s" % (self.workspaces_path, name)
        if os.path.exists(n(wrk_path)):
            shutil.rmtree( n(wrk_path) )

        # remove from cache
        self.cache["workspaces"].remove(name)
        
        # save cache to file
        self.save_workspaces()

        return (constant.OK, "success")

WrksMngr = None

def search_workspace(name):
    """search workspace by name"""
    return instance().search_workspace(name=name)
                             
def add_workspace(name):
    """add a new workspace"""
    return instance().add_workspace(name=name)
    
def del_workspace(name):
    """delete workspace"""
    return instance().delete_workspace(name=name)
    
def get_workspaces():
    """get all workspaces"""
    return instance().get_workspaces()
        
def instance():
    """Returns the singleton"""
    global WrksMngr
    return WrksMngr

def initialize(workspaces_path):
    """Instance creation"""
    global WrksMngr
    WrksMngr= WorkspacesManager(workspaces_path=workspaces_path)

def finalize():
    """Destruction of the singleton"""
    global WrksMngr
    if WrksMngr:
        del WrksMngr
        WrksMngr = None