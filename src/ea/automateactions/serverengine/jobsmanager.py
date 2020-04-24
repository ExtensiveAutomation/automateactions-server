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
import os
import json

from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serversystem import scheduler
from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import jobprocess
from ea.automateactions.serverengine import usersmanager
from ea.automateactions.serverengine import workspacesmanager

class JobsManager():
    """jobs manager"""
    def __init__(self, path_bckps):
        """init"""
        self.jobs = []
        self.path_bckps = path_bckps
        
    def get_job(self, job_id):
        """Returns the job corresponding to the id 
        passed as argument, otherwise None"""
        logger.debug("jobsmanager - get job (id=%s)" % job_id)
        
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        return None
    
    def get_jobs(self, user, workspace):
        """return jobs listing"""
        logger.debug("jobsmanager - get jobs for user=%s" % user["login"])
        
        jobs = []
        
        for job in self.jobs:
            # get the dict view of the job
            job_dict = job.to_dict()
            
            # ignore job in state different from waiting or running
            if job.job_state not in [ constant.STATE_WAITING,
                                      constant.STATE_RUNNING ]:
                continue

            # prepare the list
            if job.workspace == workspace:
                jobs.append(job_dict)
        return jobs

    def schedule_job(self, user, job_descr=None,
                           job_file=None, workspace="common",
                           sched_mode=0, sched_at=(0, 0, 0, 0, 0, 0),
                           sched_timestamp=0):
        """schedule a task to run an action"""
        logger.debug("jobsmanager - schedule job")
        
        # create the job
        job = jobprocess.Job(job_mngr=self,
                             job_descr=job_descr,
                             job_file=job_file,
                             workspace=workspace,
                             sched_mode=sched_mode,
                             sched_at=sched_at,
                             user=user,
                             path_backups=self.path_bckps)
            
        # prepare the job
        success, details = job.init()
        if success != constant.OK:
            return (constant.ERROR, details)
            
        success, details = job.build()
        if success != constant.OK:
            return (constant.ERROR, details)

        # init start time of the job
        if sched_timestamp > 0:
            job.sched_timestamp = sched_timestamp
        else:
            job.init_start_time()
        
        # save the job on the disk
        success, details = job.save()
        if success != constant.OK:
            return (constant.ERROR, details)
            
        # Register the job on the scheduler
        logger.info("jobsmanager - adding job %s in scheduler" % job.job_id)
        success, details = scheduler.add_event(ref=job.job_id,
                                               timestamp=job.sched_timestamp,
                                               callback=self.execute_job,
                                               job=job)
        if success != constant.OK:
            return (constant.ERROR, "scheduler error") 
            
        job.set_event(event=details)
        self.jobs.append(job)
        
        return (constant.OK, job.job_id)

    def execute_job(self, job):
        """execute the job"""
        logger.info("jobsmanager - starting job %s" % job.job_id)
        
        job_thread = threading.Thread(target=lambda: job.run())
        job_thread.start()
        
    def delete_job(self, job_id, user):
        """kill or cancel a task"""
        logger.info("jobsmanager - delete job (id=%s)" % job_id)
        
        job = self.get_job(job_id=job_id)
        if job is None:
            return (constant.NOT_FOUND, 'job does not exists')
        
        if user['role'] != constant.ROLE_ADMIN:
            if job.user["login"] != user['login']:
                return (constant.FORBIDDEN, 'access denied')
         
        if job.job_state == constant.STATE_RUNNING:
            logger.info("jobsmanager - killing job %s" % job.job_id)
            job.kill()
            
        if job.job_state == constant.STATE_WAITING:
            logger.info("jobsmanager - cancelling job %s" % job.job_id)
            job.cancel()
            scheduler.remove_event(job.sched_event)
            self.jobs.remove(job)
            del job
            
        return (constant.OK, 'job deleted')
   
    def reload_jobs(self):
        """reload recursive jobs"""
        logger.info("jobsmanager - reloading jobs")
  
        for fb in os.listdir(self.path_bckps):
            # load the backup job file
            with open( "%s/%s" % (self.path_bckps,fb), "r") as fh:
                job = json.loads(fh.read())
            
            # register the recursive backuped job
            self.schedule_job(user=job["user"],
                              job_descr=job["job-descr"],
                              job_file=job["job-file"],
                              workspace=job["workspace"],
                              sched_mode=job["sched-mode"],
                              sched_at=job["sched-at"],
                              sched_timestamp=job["sched-timestamp"])
            
            # remove old backup
            try:
                os.remove("%s/%s" % (self.path_bckps,fb))
            except Exception as e:
                pass
                
JobsMngr = None
def instance():
    """Returns the singleton"""
    return JobsMngr

def initialize(path_bckps):
    """Instance creation"""
    global JobsMngr
    JobsMngr = JobsManager(path_bckps=path_bckps)
    
def finalize():
    """Destruction of the singleton"""
    global JobsMngr
    if JobsMngr:
        del JobsMngr
        
def get_jobs(user, workspace):
    """return jobs listing"""
    return instance().get_jobs(user=user, workspace=workspace)
    
def reload_jobs():
    """reload jobs"""
    return instance().reload_jobs()
    
def delete_job(id, user):
    """delete job"""
    return instance().delete_job(job_id=id, user=user)

def schedule_job(user, job_descr, job_file, workspace,
                 sched_mode, sched_at):
    """schedule a job"""
    logger.info("scheduling new job "
                "user=%s mode=%s at=%s" % (user["login"],
                                           sched_mode,
                                           sched_at) )

    # all is ok, the schedule of the job can be done
    return instance().schedule_job(user=user,
                                   job_descr=job_descr,
                                   job_file=job_file,
                                   workspace=workspace,
                                   sched_mode=sched_mode,
                                   sched_at=sched_at)
