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
import json
import shutil

from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import usersmanager
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings

class ExecutionsStorage():
    """executions storage"""
    def __init__(self, repo_path):
        """repository class"""
        self.repo_path = repo_path
        self.cache = {}
        self.init_cache()
        
    def init_cache(self):
        """init the cache"""
        for entry in list(os.scandir("%s/" % (self.repo_path))):
            if entry.is_dir(follow_symlinks=False):
                try:
                    if not os.path.exists( "%s/settings.json" % entry.path):
                        continue
                        
                    with open("%s/settings.json" % entry.path, "r") as fh:
                        entry_details = fh.read()
                    
                    self.cache[entry.name] = json.loads(entry_details)
                except Exception as e:
                    logger.error("reporesults - bad entry: %s" % e)

    def get_path(self, job_id):
        """get result path"""
        results_path = "%s/%s/" % (self.repo_path, job_id)
        return os.path.normpath(results_path)
        
    def del_result(self, job_id, user):
        """delete result"""
        if job_id not in self.cache:
            return (constant.NOT_FOUND, 'result id=%s does not exist' % job_id)

        try:
            path_result = "%s/%s" % (self.repo_path, job_id)
            shutil.rmtree(path_result)
        except Exception as e:
            logger.error("reporesults - rm result failed: %s" % e)
  
        del self.cache[job_id]
        
        return (constant.OK, 'result folder removed')
    
    def get_status(self, job_id, user):
        """get status"""
        if job_id not in self.cache:
            return (constant.NOT_FOUND, 'result id=%s does not exist' % job_id)

        return (constant.OK, self.cache[job_id])
        
    def update_status(self, job_id, status):
        """update status"""
        p = self.get_path(job_id=job_id)
        
        with open("%s/status.json" % p, "w") as fh:
            fh.write("%s" % json.dumps(status))

        self.cache[job_id] = status
        
        return (constant.OK, 'result status updated')
        
    def init_status(self, job_id, status):
        """init description"""
        p = self.get_path(job_id=job_id)
        
        with open("%s/status.json" % p, "w") as fh:
            fh.write("%s" % json.dumps(status))

        self.cache[job_id] = status
        
        return (constant.OK, 'result status added')

    def reset_storage(self, job_id):
        """reset result storage"""
        try:
            p = self.get_path(job_id=job_id)
            shutil.rmtree(p)
        except Exception:
            pass
            
    def init_storage(self, job_id):
        """init result storage"""
        # add result folder
        try:
            p = self.get_path(job_id=job_id)
            os.mkdir(p, 0o755)
        except Exception as e:
            logger.error("reporesults - mkdir result failed: %s" % e)
            return (constant.ERROR, 'add result folder error')
       
        # finally put it un the cache
        self.cache[job_id] = {}
        
        return (constant.OK, 'result storage initiated')
        
    def get_logs(self, job_id, user, log_index):
        """get logs"""
        if job_id not in self.cache:
            return (constant.NOT_FOUND, 'result id=%s does not exist' % job_id)

        logs = ''
        index = 0
        p = self.get_path(job_id=job_id)
        
        if os.path.exists( "%s/job.log" % p):
            with open("%s/job.log" % p, "r") as fh:
                fh.seek(log_index)
                logs = fh.read()
                index = fh.tell()
            
        return (constant.OK, {"logs": logs,"index": index})
        
    def get_results(self, workspace, user):
        """get result according to the workspaces provided and user"""
        listing = []

        for _, res in self.cache.items():
            # ignore waiting job
            if res["job-state"] == "WAITING":
                continue

            # append the result to the list 
            if res["workspace"] == workspace:
                listing.append(res)

        listing = sorted(listing,
                         key = lambda i: i['sched-timestamp'],
                         reverse=True)
        return (constant.OK, listing)
            
RepoExecs = None

def get_path(job_id):
    """get result path"""
    return instance().get_path(job_id=job_id)
   
def get_logs(job_id, user, index):
    """get logs"""
    return instance().get_logs(job_id=job_id,
                               user=user,
                               log_index=int(index))
    
def del_result(job_id, user):
    """delete result"""
    return instance().del_result(job_id=job_id,
                                 user=user)
    
def get_status(job_id, user):
    """get status"""
    return instance().get_status(job_id=job_id,
                                 user=user)
    
def update_status(job_id, status):
    """update status"""
    return instance().update_status(job_id=job_id,
                                    status=status)
    
def init_variables(job_id, variables):
    """init variables"""
    return instance().init_variables(job_id=job_id,
                                     variables=variables)
    
def init_status(job_id, status):
    """init status"""
    return instance().init_status(job_id=job_id,
                                  status=status)

def reset_storage(job_id):
    """reset result storage"""
    return instance().reset_storage(job_id=job_id)
                                      
def init_storage(job_id):
    """init result storage"""
    return instance().init_storage(job_id=job_id)
    
def get_results(workspace, user):
    """get all results"""
    return instance().get_results(workspace=workspace,
                                  user=user)
                                  
def instance():
    """Returns the singleton"""
    return RepoExecs

def initialize(repo_path):
    """Instance creation"""
    global RepoExecs
    RepoExecs = ExecutionsStorage(repo_path=repo_path)

def finalize():
    """Destruction of the singleton"""
    global RepoExecs
    if RepoExecs:
        RepoExecs = None
