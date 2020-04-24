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
import signal
import uuid
import platform
import subprocess
import datetime
import json
       
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import jobmodel
from ea.automateactions.serverstorage import executionstorage
from ea.automateactions.joblibrary import jobtracer

n = os.path.normpath
 
class Job():
    """class for job"""
    def __init__(self, job_mngr, job_descr, job_file, workspace,
                       sched_mode, sched_at, user, path_backups):
        """job init"""
        self.job_mngr = job_mngr
        self.path_backups = path_backups
        
        # job vars
        self.job_state = constant.STATE_WAITING
        self.job_id = str(uuid.uuid4())
        self.job_descr = job_descr
        self.job_file = job_file
        # self.job_yaml = None
        self.job_name = "Job #%s" % self.job_id
        if self.job_file is not None:
            self.job_name = self.job_file
        self.job_duration = 0
        
        # schedule vars
        self.sched_mode = sched_mode
        self.sched_at = sched_at
        self.sched_timestamp = 0
        self.sched_event = None
        
        # user vars 
        self.user = user
        self.workspace = workspace

        # process vars
        self.process_id = None

    def set_state(self, state):
        """set state"""
        logger.debug("jobprocess - state update %s" % state)
        
        self.job_state = state
        executionstorage.update_status(job_id=self.job_id,
                                  status=self.to_dict())
                                                   
    def set_event(self, event):
        """set event"""
        self.sched_event = event
  
    def to_dict(self):
        """job as dict"""
        return {"job-id": self.job_id,
                "job-state": self.job_state,
                "job-name": self.job_name,
                "job-duration": self.job_duration,
                "sched-mode": self.sched_mode,
                "sched-at": self.sched_at,
                "sched-timestamp": self.sched_timestamp,
                "user": self.user,
                "workspace": self.workspace}

    def get_next_start_time(self):
        """Compute the next timestamp for recursive job"""
        _, _, _, h, mn, s = self.sched_at
        
        if self.sched_mode == constant.SCHED_DAILY:
            new_starttime = self.sched_timestamp + 60 * 60 * 24
        if self.sched_mode == constant.SCHED_HOURLY:
            new_starttime = self.sched_timestamp + 60 * 60
        if self.sched_mode == constant.SCHED_EVERY_X:
            new_starttime = self.sched_timestamp + 60 * 60 * h + 60 * mn + s
        if self.sched_mode == constant.SCHED_WEEKLY:
            new_starttime = self.sched_timestamp + 7 * 24 * 60 * 60

        return new_starttime
        
    def init_start_time(self):
        """get timestamp of the start"""
        logger.debug("jobprocess - init start time")
        
        y, m, d, h, mn, s = self.sched_at
        cur_dt = time.localtime()
        
        if self.sched_mode == constant.SCHED_NOW:
            timestamp = time.time()
            
        if self.sched_mode == constant.SCHED_AT:
            dt = datetime.datetime(y, m, d, h, mn, s, 0)
            timestamp = time.mktime(dt.timetuple())
            
        if self.sched_mode == constant.SCHED_DAILY:
            next_dt = datetime.datetime(cur_dt.tm_year, cur_dt.tm_mon,
                                        cur_dt.tm_mday, h, mn, s, 0)
            timestamp = time.mktime(next_dt.timetuple())
            
        if self.sched_mode == constant.SCHED_HOURLY:
            next_dt = datetime.datetime(cur_dt.tm_year, 
                                        cur_dt.tm_mon, 
                                        cur_dt.tm_mday,
                                        cur_dt.tm_hour, 
                                        mn, s, 0)
            timestamp = time.mktime(next_dt.timetuple())
            
        if self.sched_mode == constant.SCHED_EVERY_X:
            next_dt = datetime.datetime(cur_dt.tm_year, 
                                        cur_dt.tm_mon,
                                        cur_dt.tm_mday,
                                        cur_dt.tm_hour,
                                        cur_dt.tm_min,
                                        cur_dt.tm_sec, 0)
            next_dt += datetime.timedelta(hours=h, minutes=mn, seconds=s)
            timestamp = time.mktime(next_dt.timetuple())
            
        if self.sched_mode == constant.SCHED_WEEKLY: 
            next_dt = datetime.datetime(cur_dt.tm_year, cur_dt.tm_mon,
                                        cur_dt.tm_mday, h, mn, s, 0)
            delta = datetime.timedelta(days=1)
            while next_dt.weekday() != d:
                next_dt = next_dt + delta
            timestamp = time.mktime(next_dt.timetuple())
            
        self.sched_timestamp = timestamp
        
        # pershap the timestamp is too old
        # compute the next start time
        # only for recursive jobs
        if self.is_recursive():
            if timestamp < time.time():
                self.sched_timestamp = self.get_next_start_time()

    def is_recursive(self):
        """job is recursive"""
        if self.sched_mode > 1:
            return True
        return False
        
    def kill(self):
        """kill the job"""
        logger.debug("jobprocess - kill the job")
        
        if self.process_id is None:
            return constant.NOT_FOUND
         
        success = constant.ERROR
        
        if platform.system() == "Windows":
            kill_cmd = ["taskkill"]
            kill_cmd.append("/PID")
            kill_cmd.append("%s" % self.process_id)
            kill_cmd.append("/F")
            p = subprocess.Popen(kill_cmd, stdout=subprocess.PIPE)
            p.wait()
            if not p.returncode:
                success = constant.OK
        else:
            try:
                os.kill(self.process_id, signal.SIGKILL)
                success = constant.OK
            except Exception as e:
                logger.error("jobprocess - unable to kill %s" % e)
        return success

    def cancel(self):
        """cancel the result"""
        logger.debug("jobprocess - cancel the job")
        
        # remove the reset storage
        executionstorage.reset_storage(job_id=self.job_id)
        
        # delete job from disk for recursive one
        self.delete()
        
        return (constant.OK, "success")
        
    def init(self):
        """init result storage"""
        logger.debug("jobprocess - init result storage")
        
        success, details = executionstorage.init_storage(job_id=self.job_id)
        if success != constant.OK:
            return (constant.ERROR, details)
 
        # save job status in result
        success, details = executionstorage.init_status(job_id=self.job_id,
                                                   status=self.to_dict())
        if success != constant.OK:
            return (constant.ERROR, details)
            
        return (constant.OK, "success")
        
    def build(self):
        """build the job"""
        logger.debug("jobprocess - build python job")

        success, details = jobmodel.create_pyjob(yaml_file=self.job_file,
                                                 yaml_str=self.job_descr,
                                                 workspace=self.workspace,
                                                 user=self.user,
                                                 job_id=self.job_id)
        if success != constant.OK:
            return (constant.ERROR, details)
            
        # all is OK
        return (constant.OK, "success")

    def save(self):
        """save the job on the disk"""
        logger.debug("jobprocess - save the job on disk")
        
        if self.is_recursive():
            p = "%s/%s.json" % (self.path_backups,
                                self.job_id)
            p = os.path.normpath(p)
            with open(p, "w") as fh:
                job_dict = self.to_dict()
                job_dict["job-file"] = self.job_file
                job_dict["job-descr"] = self.job_descr
                fh.write("%s" % json.dumps(job_dict))
            
        return (constant.OK, "success")

    def delete(self):
        """delete the job from disk"""
        logger.debug("jobprocess - delete the job from disk")
        
        if self.is_recursive():
            p = "%s/%s.json" % (self.path_backups,
                                self.job_id)
            p = os.path.normpath(p)
            
            try:
                os.remove(p)
            except Exception:
                pass
        
        return (constant.OK, "success")
        
    def run(self):
        """run thread"""
        logger.debug("jobprocess - run the job")
        
        # prepare next run if the job is recursive
        if self.is_recursive():
            # delete from disk the current backuped job
            self.delete()
            
            # register a new job with the same parameters
            new_start_time = self.get_next_start_time()
            self.job_mngr.schedule_job(user=self.user,
                                       job_descr=self.job_descr,
                                       job_file=self.job_file,
                                       workspace=self.workspace,
                                       sched_mode=self.sched_mode,
                                       sched_at=self.sched_at,
                                       sched_timestamp=new_start_time)
        
        # keep the start time of the run
        start_time = time.time()
        
        # change state to running
        self.set_state(state=constant.STATE_RUNNING)
        
        # get python path according to the os
        if platform.system() == "Windows":
            executable = settings.cfg['paths']['python-windows']
        else:
            executable = settings.cfg['paths']['python-linux']
        
        # prepare the path of the job
        p = executionstorage.get_path(job_id=self.job_id)
        job_path = "%s/jobrunner.py" % p
        job_path = n(job_path)
        
        jobtracer.initialize(result_path=n(p))
        
        args = [executable]
        args.append(job_path)
        
        # run the job in a separate process
        jobtracer.instance().log_job_started()

        try:
            p = subprocess.Popen(args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            self.process_id = p.pid
        except Exception as e:
            logger.error('jobprocess - unable to run job: %s' % e)
            self.set_state(state=constant.STATE_FAILURE)
        else:
            # wait the process to complete
            p.wait()
            retcode = p.returncode
            
            # compute the duration of the job
            self.job_duration = time.time() - start_time
            
            # set the final state of the job SUCCESS or FAILURE?
            if retcode == 0:
                self.set_state(state=constant.STATE_SUCCESS)
            else:
                err_str = p.stderr.read().decode("utf8")
                if len(err_str):
                    jobtracer.instance().log_job_error(message=err_str)

                self.set_state(state=constant.STATE_FAILURE)

        job_result = constant.RETCODE_LIST.get(retcode, constant.STATE_FAILURE)
        jobtracer.instance().log_job_stopped(result=job_result,
                                             duration=self.job_duration)
        jobtracer.finalize()
        logger.info('jobprocess - job %s terminated' % self.job_id)