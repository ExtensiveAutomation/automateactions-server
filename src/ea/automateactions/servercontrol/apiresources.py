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

import json

from pycnic.core import Handler
from pycnic.errors import HTTP_401, HTTP_400, HTTP_500, HTTP_403

from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import jobsmanager
from ea.automateactions.serverengine import workspacesmanager
from ea.automateactions.serverengine import globalsmanager
from ea.automateactions.serverengine import sessionsmanager
from ea.automateactions.serverengine import usersmanager
from ea.automateactions.serverstorage import actionstorage
from ea.automateactions.serverstorage import snippetstorage
from ea.automateactions.serverstorage import executionstorage
           
def get_user(request):
    """Lookup a user session"""
    profile = {}

    sess_id = request.cookies.get("session_id")
    if sess_id is not None:
        s = sessionsmanager.get_session(sess_id=sess_id)
        if s is None:
            raise HTTP_401("invalid session")
        u = usersmanager.search_user(login=s["login"])
        if u is None:
            raise HTTP_401("unknown user")

        (login, details) = list(u.items())[0]
        profile["login"] = login
        profile["role"] = details["role"]
        return profile
            
    auth = request.get_header(name="Authorization", default=None)
    if auth is None:
        raise HTTP_401("authorization header not detected")
        
    auth_result, u = sessionsmanager.do_basic_auth(auth=auth)
    if not auth_result:
        raise HTTP_401("authentification failed")

    (login, details) = list(u.items())[0]
    profile["login"] = login
    profile["role"] = details["role"]
    return profile

def fix_encoding_uri_param(p):
    try:
        p = p.encode("latin1").decode()
    except UnicodeError:
        pass
    return p

class SessionHandler(Handler):
    """Session handler for rest requests""" 
    def delete(self):
        """delete session"""
        msg = "Not logged in"
        
        sess_id = self.request.cookies.get("session_id", None)
        if sess_id is not None:
            sessionsmanager.del_session(sess_id=sess_id)
            self.response.delete_cookie("session_id")
            msg = "logged out"
            
        return {"cmd": self.request.path, "message": msg}
        
    def post(self):
        """create session"""
        # checking query request 
        login = self.request.data.get("login")
        if login is None:
            raise HTTP_400("login is expected")
        
        password = self.request.data.get("password")
        if password is None:
            raise HTTP_400("password is expected")
        
        # check user access
        auth_ret, u, sess_id = sessionsmanager.do_session_auth(login=login,
                                                               password=password)
        if not auth_ret:
            raise HTTP_401("authentification failed")

        # set sessionid on cookie
        self.response.set_cookie(key="session_id", value=sess_id,
                                 expires='', path='/', domain="")

        _rsp = {
            "cmd": self.request.path,
            "message": "Logged in",
            "session_id": sess_id,
            "expires": settings.cfg["session"]["max-expiry-age"],
            "role": u[login]["role"],
            "api_login": login,
            "api_secret": u[login]['secrets']["basic"]
        }
        return _rsp
        
    def options(self):
        """cors support"""
        return {}  
        
class UserPasswordHandler(Handler):
    """User password handler for rest requests""" 
    def delete(self, login):
        """delete user"""
        user_profile = get_user(request=self.request)
        login = fix_encoding_uri_param(login)

        if user_profile['role'] != constant.ROLE_ADMIN:
            raise HTTP_403("access refused")
            
        success, details = usersmanager.reset_pwd(login=login)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "password successfully reseted"} 
                
    def patch(self, login):
        """update user"""
        user_profile = get_user(request=self.request)
        login = fix_encoding_uri_param(login)

        if user_profile['role'] != constant.ROLE_ADMIN:
            if user_profile["login"] != login:
                raise HTTP_403("access denied")

        cur_pwd = self.request.data.get("current-password")
        if cur_pwd is None:
            raise HTTP_400("Current password is expected")

        new_pwd = self.request.data.get("new-password")
        if new_pwd is None:
            raise HTTP_400("New password is expected")
        if not len(new_pwd):
            raise HTTP_400("password name cannot be empty")

        success, details = usersmanager.update_pwd(login=login,
                                                   new_pwd=new_pwd,
                                                   cur_pwd=cur_pwd)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "password successfully updated"}
                         
    def options(self, id=None):
        """cors support"""
        return {}
               
class UserHandler(Handler):
    """User handler for rest requests""" 
    def get(self, login=None):
        """get users"""
        user_profile = get_user(request=self.request)

        # return all users 
        if login is None:
            # security checks
            if user_profile['role'] != constant.ROLE_ADMIN:
                raise HTTP_403("access refused")

            success, details = usersmanager.get_users()
        
        # return one user
        else:
            
            login = fix_encoding_uri_param(login)

            # security checks
            if user_profile['role'] != constant.ROLE_ADMIN:
                if user_profile["login"] != login:
                    raise HTTP_403("access refused")

            #if login not in 
            success, details = usersmanager.get_user(login=login)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "users": details}
        
    def post(self):
        """add user"""
        user_profile = get_user(request=self.request)
        
        # checking level access to this ressource
        if not user_profile['role'] == constant.ROLE_ADMIN:
            raise HTTP_403("access refused")
        
        # checking query request 
        login = self.request.data.get("login")
        if login is None:
            raise HTTP_400("login is expected")
        if not len(login):
            raise HTTP_400("login name cannot be empty")

        password = self.request.data.get("password")
        if password is None:
            raise HTTP_400("password is expected")
        if not len(password):
            raise HTTP_400("password name cannot be empty")

        role = self.request.data.get("role")
        if role not in constant.ROLE_LIST:
            raise HTTP_400("bad role provided")
            
        success, details = usersmanager.add_user(role=role,
                                                 login=login,
                                                 password=password)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "user successfully added"}
                
    def patch(self, login):
        """update user"""
        user_profile = get_user(request=self.request)
        
        # checking level access to this ressource
        if user_profile['role'] != constant.ROLE_ADMIN:
            raise HTTP_403("access refused")
        
        # checking query request
        login = fix_encoding_uri_param(login)
        role = self.request.data.get("role")

        if role not in constant.ROLE_LIST:
            raise HTTP_400("bad role provided")

        success, details = usersmanager.update_role(login=login,
                                                    role=role)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "role successfully updated"}
                
    def delete(self, login):
        """delete user"""
        user_profile = get_user(request=self.request)

        if user_profile['role'] != constant.ROLE_ADMIN:
            raise HTTP_403("access refused")

        login = fix_encoding_uri_param(login)

        if user_profile["login"] == login:
            raise HTTP_403("deletion not authorized")

        success, details = usersmanager.delete_user(login=login)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "user successfully removed"}
                
    def options(self, id=None):
        """cors support"""
        return {}
        
class GlobalsHandler(Handler):
    """Globals environment handler for rest requests"""
    def get(self, entry_name=None):
        """return one entry according to id or all"""
        workspace = self.request.args.get("workspace", "common")

        success, details = globalsmanager.get_entries(workspace=workspace)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "globals": details}
                
    def post(self):
        """add globals entries"""
        workspace = self.request.args.get("workspace", "common")

        # checking query request 
        var_value = self.request.data.get("value")
        if var_value is None:
            raise HTTP_400("Value is expected")

        success, details = globalsmanager.saves_entries(content=var_value,
                                                        workspace=workspace)
        if success != constant.OK:
            raise HTTP_500(details)
            
        return {"cmd": self.request.path,
                "message": "success",}
           
    def options(self, entry_name=None):
        """cors support"""
        return {}
        
class WorkspacesHandler(Handler):
    """Project handler for rest requests"""
    def get(self):
        """Return one project according to id or all"""
        success, details = workspacesmanager.get_workspaces()
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "workspaces": details}
                
    def post(self):
        """Add a new project, only for administrator"""
        user_profile = get_user(request=self.request)

        # checking level access to this ressource
        if user_profile['role'] != constant.ROLE_ADMIN:
            raise HTTP_403("access refused")
            
        # checking request
        name = self.request.data.get("name")
        if name is None:
            raise HTTP_400("workspace name is mandatory")
        if not len(name):
            raise HTTP_400("workspace name cannot be empty")

        success, details = workspacesmanager.add_workspace(name=name)
        if success != constant.OK:
            raise HTTP_500(details)
            
        return {"cmd": self.request.path,
                "message": "workspace successfully added",
                "project-id": details}
                
    def delete(self, name):
        """Delete a workpsace, only for administrator"""
        user_profile = get_user(request=self.request)
        name = fix_encoding_uri_param(name)

        # checking level access to this ressource
        if user_profile['role'] != constant.ROLE_ADMIN:
            raise HTTP_403("access refused")
            
        success, details = workspacesmanager.del_workspace(name=name)
        if success != constant.OK:
            raise HTTP_500(details)
        
        return {"cmd": self.request.path,
                "message": "project successfully removed"}
                
    def options(self, id=None):
        """cors support"""
        return {}
        
class JobsHandler(Handler):
    """Job handler for rest requests"""
    def get(self, id=None):
        """Return one task according to id or all"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")

        jobs = jobsmanager.get_jobs(user=user_profile, workspace=workspace)

        return {"cmd": self.request.path,
                "jobs": jobs}
        
    def post(self):
        """Add a new task"""
        user_profile = get_user(request=self.request)

        yaml_file = self.request.data.get("yaml-file")
        yaml_content = self.request.data.get("yaml-content")
        if yaml_file is None and yaml_content is None:
            raise EmptyValue("yaml content or file is expected")
        
        workspace = self.request.data.get("workspace", "common")
        sched_mode = self.request.data.get("mode", 0)
        sched_at = self.request.data.get("schedule-at", (0, 0, 0, 0, 0, 0) )

        if sched_mode not in constant.SCHED_MODE:
            raise HTTP_400("invalid sched mode")
            
        success, details = jobsmanager.schedule_job(
                                                    user=user_profile,
                                                    job_descr=yaml_content,
                                                    job_file=yaml_file,
                                                    workspace=workspace,
                                                    sched_mode=sched_mode,
                                                    sched_at=sched_at,
                                                )
        if success != constant.OK:
            raise HTTP_500(details)
            
        return {"cmd": self.request.path,
                "message": "job successfully scheduled",
                "id": details}
                
    def delete(self, id):
        """delete task, kill or cancel according to the current state"""
        user_profile = get_user(request=self.request)

        success, details = jobsmanager.delete_job(id=id,
                                                  user=user_profile)
        if success != constant.OK:
            raise HTTP_500(details)
            
        return {"cmd": self.request.path,
                "message": "job successfully deleted"}
                
    def options(self, id=None):
        """cors support"""
        return {}
     
class ExecutionsHandler(Handler):
    """History handler for rest requests"""   
    def get(self, id=None):
        """return all history according to the project-id"""
        user_profile = get_user(request=self.request)
        
        log_index = self.request.args.get("log_index", 0)
        workspace = self.request.args.get("workspace", "common")
        
        rsp = {"cmd": self.request.path}

        if id is not None:
            success, details = executionstorage.get_status(job_id=id,
                                                      user=user_profile)
            if success != constant.OK:
                raise HTTP_500(details)
            rsp.update(details)
            
            success, details = executionstorage.get_logs(job_id=id,
                                                    user=user_profile,
                                                    index=log_index)
            if success != constant.OK:
                raise HTTP_500(details)
            rsp.update(details)
        
        else:
            success, details = executionstorage.get_results(workspace=workspace,
                                                       user=user_profile)
            if success != constant.OK:
                raise HTTP_500(details)
            rsp.update({"listing": details} )
            
        return rsp
        
    def delete(self, id=None):
        """delete result"""
        user_profile = get_user(request=self.request)

        success, details = executionstorage.del_result(job_id=id,
                                                  user=user_profile)
        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": "success"} 
                     
    def options(self, id=None):
        """cors support"""
        return {}

class ActionsHandler(Handler):
    """Action handler for rest requests"""
    def get(self, filename=None):
        """return actions listing according to the project-id or read a specific action file"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")

        if filename is None:
            success, details = actionstorage.instance().get_files(workspace=workspace,
                                                                user=user_profile)
        else:
            filename = fix_encoding_uri_param(filename)
            success, details = actionstorage.instance().read_file(filename=filename,
                                                                workspace=workspace,
                                                                user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "actions": details}

    def post(self, item_path):
        """add action"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        content_file = self.request.data.get("content", "")

        success, details = actionstorage.instance().add(item_path=item_path,
                                                      workspace=workspace,
                                                      user=user_profile,
                                                      content_file=content_file)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def put(self, item_path):
        """update item"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        success, details = actionstorage.instance().duplicate(item_path=item_path,
                                                            workspace=workspace,
                                                            user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def patch(self, item_path):
        """update item"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        new_name = self.request.data.get("name")

        success, details = actionstorage.instance().update(item_path=item_path,
                                                         workspace=workspace,
                                                         user=user_profile,
                                                         new_name=new_name)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def delete(self, item_path):
        """delete item like a file or folder"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        success, details = actionstorage.instance().delete(item_path=item_path,
                                                         workspace=workspace,
                                                         user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def options(self, id=None):
        """cors support"""
        return {}

class SnippetsHandler(Handler):
    """Snippets handler for rest requests"""
    def get(self, filename=None):
        """return snippets listing according to the project-id or read a specific script"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")

        if filename is None:
            success, details = snippetstorage.instance().get_files(workspace=workspace,
                                                                user=user_profile)
        else:
            filename = fix_encoding_uri_param(filename)
            success, details = snippetstorage.instance().read_file(filename=filename,
                                                                workspace=workspace,
                                                                user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "snippets": details}

    def post(self, item_path):
        """add script"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        content_file = self.request.data.get("content", "")

        success, details = snippetstorage.instance().add(item_path=item_path,
                                                      workspace=workspace,
                                                      user=user_profile,
                                                      content_file=content_file)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def put(self, item_path):
        """update item"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        success, details = snippetstorage.instance().duplicate(item_path=item_path,
                                                            workspace=workspace,
                                                            user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def patch(self, item_path):
        """update item"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        new_name = self.request.data.get("name")

        success, details = snippetstorage.instance().update(item_path=item_path,
                                                         workspace=workspace,
                                                         user=user_profile,
                                                         new_name=new_name)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def delete(self, item_path):
        """delete item like a file or folder"""
        user_profile = get_user(request=self.request)
        workspace = self.request.args.get("workspace", "common")
        item_path = fix_encoding_uri_param(item_path)

        success, details = snippetstorage.instance().delete(item_path=item_path,
                                                         workspace=workspace,
                                                         user=user_profile)

        if success != constant.OK:
            raise HTTP_500(details)

        return {"cmd": self.request.path,
                "message": details}

    def options(self, id=None):
        """cors support"""
        return {}
         