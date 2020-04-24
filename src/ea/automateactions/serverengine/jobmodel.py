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
import yaml
import re

from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import workspacesmanager
from ea.automateactions.serverengine import usersmanager
from ea.automateactions.serverengine import globalsmanager
from ea.automateactions.serverstorage import actionstorage
from ea.automateactions.serverstorage import snippetstorage
from ea.automateactions.serverstorage import executionstorage

n = os.path.normpath

    
def load_yamlstr(yaml_str):
    """open and read yaml string"""
    logger.debug('jobmodel - loading yaml from string')
    
    try:
        yaml_job = yaml.safe_load(yaml_str)
    except Exception as e:
        error_str = "yaml loading error - %s" % e
        logger.error('jobmodel - %s' % error_str)
        return (constant.ERROR, error_str)

    return (constant.OK, yaml_job)
    
def load_yamlfile(yaml_file, workspace, user, repo):
    """load yaml file"""
    logger.debug('jobmodel - loading yaml from file')
    
    if repo == constant.REPO_ACTIONS:
        repo_path = actionstorage.instance().get_path(workspace=workspace)
        file_path = n("%s/%s" % (repo_path,yaml_file))
    elif repo == constant.REPO_SNIPPETS:
        repo_path = snippetstorage.instance().get_path(workspace=workspace)
        file_path = n("%s/%s" % (repo_path,yaml_file))
    else:
        file_path = n(yaml_file)
      
    if not os.path.exists(file_path):
        error_str = "file=%s not found " % yaml_file
        error_str += "in workspace=%s" % workspace
        logger.error('jobmodel - %s' % error_str)
        return (constant.NOT_FOUND, error_str)
      
    with open(file_path, 'r') as fd:
        yaml_str = fd.read()
    
    return load_yamlstr(yaml_str=yaml_str)

def tab(code, nb_tab=1):
    """add tabulation for each lines"""
    space = ' '*4
    indent_char = space * nb_tab
    ret = []
    for line in code.splitlines():
        ret.append("%s%s" % (indent_char, line))
    return '\n'.join(ret)
     
def create_pyjob(yaml_file, yaml_str, workspace, user, job_id):
    """create pyjob"""
    logger.debug('jobmodel - creating python job')
    
    # get the job path according to the id
    job_path = executionstorage.get_path(job_id=job_id)

    # checking if yaml is provided
    if yaml_file is None and yaml_str is None:
        error_str = "no yaml file or content provided"
        logger.error('jobmodel - %s' % error_str)
        return (constant.ERROR, error_str)

    # loading the yaml 
    if yaml_str is not None:
        yaml_valid, yaml_job = load_yamlstr(yaml_str=yaml_str)
  
    if yaml_file is not None:
        yaml_valid, yaml_job = load_yamlfile(yaml_file=yaml_file,
                                             workspace=workspace,
                                             user=user,
                                             repo=constant.REPO_ACTIONS)
        
    if yaml_valid != constant.OK:
        return (constant.ERROR, yaml_job)

    # create python scripts
    success, details = create_pyjob_runner(job_yaml=yaml_job,
                                           job_path=job_path,
                                           job_id=job_id,
                                           workspace=workspace,
                                           user=user)
    if success != constant.OK:
        return (constant.ERROR, details)

    return (constant.OK, "success")
 
def create_pyjob_runner(job_yaml, job_path, job_id, workspace, user):
    """create python job runner"""
    logger.debug('jobmodel - creating python job runner')

    # loading globals variables
    globals_file = '%s/%s/%s/globals.yml' % ( settings.get_app_path(),
                                              settings.cfg['paths']['workspaces'],
                                              workspace )
    globals_valid, yaml_globals = load_yamlfile(yaml_file=globals_file,
                                                workspace=workspace,
                                                user=user,
                                                repo=constant.REPO_WORKSPACES)
    if globals_valid != constant.OK:
        logger.error('jobmodel - invalid globals variables')
        return (constant.ERROR, {})

    script = []
    script.append("#!/usr/bin/python")
    script.append("# -*- coding: utf-8 -*-")
    script.append("")
    script.append("import sys")
    script.append("import os")
    script.append("import time")
    script.append("import json")
    script.append("import traceback")
    script.append("")
    script.append("p = os.path.dirname(os.path.abspath(__file__))")
    script.append("root_path = os.sep.join(p.split(os.sep)[:-5])")
    script.append("sys.path.insert(0, root_path)")
    script.append("")
    script.append("from ea.automateactions.joblibrary import jobtracer")
    script.append("from ea.automateactions.joblibrary import jobhandler")
    script.append("from ea.automateactions.joblibrary import jobsnippet")
    script.append("from ea.automateactions.joblibrary import datastore")
    script.append("")
    script.append("jobtracer.initialize(result_path=p)")
    script.append("")
    script.append("sys.stderr = jobtracer.StdWriter(mode_err=True)")
    script.append("sys.stdout = jobtracer.StdWriter()")
    script.append("")
    script.append("jobhandler.initialize(globals=%s)" % yaml_globals)
    script.append("datastore.initialize()")
    script.append("")
    script.append( write_snippets(job_path, job_yaml,
                                  job_id, workspace, user) )
    script.append("")
    script.append("jobhandler.instance().start()")
    script.append("jobhandler.finalize()")
    script.append("ret_code = jobhandler.get_retcode()")
    script.append("sys.exit(ret_code)")

    with open(n("%s/jobrunner.py" % job_path), 'wb') as fd:
        fd.write('\n'.join(script).encode('utf-8'))
  
    return (constant.OK, "success")

def write_snippets(job_path, job_yaml, job_id, workspace, user):
    """create python snippets"""
    script = []
    if "python" in job_yaml:
        script.append("import snippet0")
        write_snippet(snippet_id=0,
                      snippet_name="",
                      snippet_src=job_yaml["python"],
                      snippet_descr="",
                      snippet_when={},
                      job_path=job_path,
                      job_id=job_id,
                      user=user)
        script.append('snippet = jobsnippet.Snippet(id=0, name="python", vars=%s)' % job_yaml.get("variables", {}) )
        script.append("jobhandler.register(snippet=snippet, cb=snippet0.run_snippet)")
        script.append("")
        
    elif "snippets" in job_yaml:
        i = 1
        for snippet in job_yaml["snippets"]:
            script.append("import snippet%s" % i)
            
            snippet_name, snippet_dict= tuple(snippet.items())[0]
            snippet_descr = snippet_dict.get("description", "")
            snippet_file = snippet_dict.get("execute", "/undefined")
            snippet_when = snippet_dict.get("when", {})
            snippet_with = snippet_dict.get("with", {})

            yaml_valid, snippet_yaml = load_yamlfile(yaml_file=snippet_file,
                                                     workspace=workspace,
                                                     user=user,
                                                     repo=constant.REPO_SNIPPETS)
            if yaml_valid != constant.OK:
                src_err = []
                src_err.append( 'snippet.error("%s")' % snippet_yaml )
                snippet_yaml = {}
                snippet_yaml["python"] = "\n".join(src_err)

            # subtitute variables
            vars_regex = r"(?P<vars>\$\{\{variables\.(?P<vars_keys>[\w-]+(?:\.[\w-]+)*)\}\})"
            for k,v in snippet_with.items():
                if isinstance(v, str):
                    matched = re.findall(vars_regex, v)
                    
                    for el in matched:
                        pattern, keys = el
                        keys_list = keys.split(".")

                        nv = job_yaml["variables"].get(keys_list[0], None)
                        for k in keys_list[1:]:
                            if isinstance(nv, dict):
                                nv = nv.get(k, None)

                        if pattern == v:
                            snippet_with[k] = nv
                            break

                        snippet_with[k] = v.replace(pattern, "%s" % nv, 1)

            snippet_vars = snippet_yaml.get("variables", {})
            for k,v in snippet_with.items():
                if k in snippet_vars:
                    snippet_vars[k] = v

            # write snippet
            write_snippet(snippet_id=i,
                          snippet_name=snippet_name,
                          snippet_src=snippet_yaml["python"],
                          snippet_descr=snippet_descr,
                          snippet_when=snippet_when,
                          job_path=job_path,
                          job_id=job_id,
                          user=user)

            script.append('snippet = jobsnippet.Snippet(id=%s, name="%s", when=%s, vars=%s, vars_sub=%s)' % (i,
                                                                                                             snippet_name,
                                                                                                             snippet_when,
                                                                                                             snippet_vars,
                                                                                                             snippet_with
                                                                                                            ))
            script.append("jobhandler.register(snippet=snippet, cb=snippet%s.run_snippet)" % i )
            script.append("")
            
            i += 1
    else:
        script.append("pass")
    return "\n".join(script)

def write_snippet(snippet_id, snippet_name, snippet_src, snippet_descr, snippet_when,
                  job_path, job_id, user):
    """write python snippet"""
    logger.debug('jobmodel - creating python snippet')
    
    script = []
    script.append("#!/usr/bin/python")
    script.append("# -*- coding: utf-8 -*-")
    script.append("")
    script.append("def run_snippet(snippet):")
    script.append(tab("import time"))
    script.append(tab("import traceback"))
    script.append(tab("from ea.automateactions.joblibrary import jobsnippet"))
    script.append(tab("step_start_time = time.time()"))
    script.append(tab('snippet.begin(description="%s")' % snippet_descr))
    script.append(tab("try:"))
    
    script.append(tab(write_snippet_import(snippet_id=snippet_id), nb_tab=2))
    script.append(tab("snippet.done()", nb_tab=2))
    script.append(tab("except jobsnippet.FailureException as e:"))
    script.append(tab("snippet.error(message=e)", nb_tab=2))
    script.append(tab("except Exception as e:"))
    script.append(tab("tb = traceback.format_exc()", nb_tab=2))
    script.append(tab("snippet.error(message=tb)", nb_tab=2))
    script.append(tab("step_duration = time.time() - step_start_time"))
    script.append(tab("snippet.ending(duration=step_duration)"))

    with open(n("%s/snippet%s.py" % (job_path, snippet_id)), 'wb') as fd:
        fd.write('\n'.join(script).encode('utf-8'))

    write_snippet_code(snippet_id=snippet_id,
                       snippet_src=snippet_src,
                       job_path=job_path)
    
def write_snippet_import(snippet_id):
    """write snippet python import"""
    logger.debug('jobmodel - write python snippet import')
    
    script = []
    script.append("try:")
    script.append(tab("from snippet%s_code import run_snippet_code" % snippet_id))
    script.append(tab("run_snippet_code(snippet=snippet)"))
    script.append("except SyntaxError as err:")
    script.append(tab("err.lineno = err.lineno - 1"))
    script.append(tab("raise"))
    return "\n".join(script)
    
def write_snippet_code(snippet_id, snippet_src, job_path):
    """create python snippet source"""
    logger.debug('jobmodel - inject python source')
    script = []
    script.append("def run_snippet_code(snippet):")
    script.append(tab(snippet_src))
    
    with open(n("%s/snippet%s_code.py" % (job_path, snippet_id)), 'wb') as fd:
        fd.write('\n'.join(script).encode('utf-8'))
