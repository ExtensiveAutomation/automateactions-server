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
import threading
import time
import uuid
import base64
import hashlib
import urllib
from binascii import hexlify
try:
    import ldap3
except ImportError:
    ldap3 = None
    
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings
from ea.automateactions.serverengine import constant
from ea.automateactions.serverengine import usersmanager

class SessionsManager(threading.Thread):
    """sessions manager"""
    def __init__(self):
        """init class"""
        threading.Thread.__init__(self)
        self.lock = threading.RLock()
        self.event = threading.Event()
        self.running = True
        
        self.sessions = {}
        
        self.lease = settings.cfg['session']['max-expiry-age']
        self.expire = settings.cfg['session']['timeout-cleanup']

        
        # start the thread
        self.start()

    def gen_sess_id(self):
        """returns a random, 45-character session ID."""
        logger.debug("sessionsmanager - generate session id")
        uuid_val = (uuid.uuid4().hex + uuid.uuid4().hex).encode('utf-8')
        session_id = base64.b64encode(uuid_val)[:45]
        return session_id.decode('utf8')

    def delete_session(self, sess_id):
        """delete session"""
        logger.debug("sessionsmanager - del session id=%s" % sess_id)
        if sess_id in self.sessions:
            del self.sessions[sess_id]
        
    def get_session(self, sess_id):
        """get session"""
        logger.debug("sessionsmanager - get session id=%s" % sess_id)
        
        if sess_id in self.sessions:
            return self.sessions[sess_id]
        return None
        
    def do_basic_auth(self, auth):
        """do basic auth"""
        logger.debug("sessionsmanager - do basic auth ")
        
        u = None
        success = False
        if not auth.startswith("Basic "):
            return (success,u)
            
        try:
            auth_val = auth.split("Basic ")[1].strip()
            
            decoded = base64.b64decode(auth_val.encode())
            decoded = decoded.decode()
            
            apikey_id, apikey_secret = decoded.rsplit(":", 1)
            
            logger.debug("sessionsmanager - basic auth "
                         "decoded for user=%s" % apikey_id)
            
            u = usersmanager.search_user(login=apikey_id)
            if u is not None:
                if u[apikey_id]["secrets"]["basic"] == apikey_secret:
                    logger.debug("sessionsmanager - basic auth "
                                "success for user=%s" % apikey_id)
                    success = True
                else:
                    logger.debug("sessionsmanager - basic auth "
                                 "failed for user=%s" % apikey_id)
                    success = False
            else:
                logger.debug("sessionsmanager - basic auth "
                             "user=%s does not exist" % apikey_id)
                success = False
        except Exception as e:
            logger.error("sessionsmanager - unable to "
                         "decode basic auth: %s" % e)
        return (success,u)
        
    def do_session_auth(self, login, password):
        """do session auth"""
        logger.debug("sessionsmanager - do session auth "
                     "for login=%s" % login)
        
        success = False
        sess_id = None
        u = None
        
        # search login in cache users
        u = usersmanager.search_user(login=login)
        if u is None:
            logger.error("sessionsmanager - auth failed "
                         "login=%s not found" % login)
            return (success,u, sess_id)
            
        # auth ldap ?
        if settings.cfg['ldap']['authbind']:
            success = self.do_ldap_auth(login=login, password=password)

        # auth session ?
        else:
            hash_pwd = usersmanager.genpass_hash(password=password)
            if u[login]['secrets']["session"] == hash_pwd:
                success = True
            
        if not success:
            logger.error("sessionsmanager - auth failed "
                         "for login %s" % login)
            return (success, u, sess_id)
                
        # generate session id
        sess_id = self.gen_sess_id()
        last_activity = time.time()
        end = time.gmtime(last_activity + self.lease)
        expires = time.strftime("%a, %d-%b-%Y %T GMT", end)
        
        # save-it
        self.sessions[sess_id] = {"last-activity": last_activity,
                                  "login": login,
                                  "expires": expires}
              
        # valid auth
        logger.debug("sessionsmanager - auth success "
                     "for login %s" % login)
        return (success, u, sess_id)
        
    def do_ldap_auth(self, login, password):
        """do ldap auth"""
        logger.debug("sessionsmanager - do ldap auth for login=%s" % login)
        
        if ldap3 is None:
            logger.error("auth failed - ldap library missing")
            return False
        
        # get ldap settings
        ldap_host_list = settings.cfg['ldap']['host']
        ldap_dn_list = settings.cfg['ldap']['dn']
        
        # define ldap server(s)
        servers_list = []
        for host in ldap_host_list:
            use_ssl = False
            ldap_port = 386
            # parse the url to extract scheme host and port
            url_parsed = urllib.parse.urlparse(host)

            if url_parsed.scheme == "ldaps":
                use_ssl = True
                ldap_port = 636

            if ":" in url_parsed.netloc:
                ldap_host, ldap_port = url_parsed.netloc.split(":")
            else:
                ldap_host = url_parsed.netloc

            server = ldap3.Server(ldap_host,
                                  port=int(ldap_port),
                                  use_ssl=use_ssl)
            servers_list.append(server)
            
        last_auth_err = ""
        for bind_dn in ldap_dn_list:
            c = ldap3.Connection(servers_list,
                                 user=bind_dn % login,
                                 password=password)

            # perform the Bind operation
            auth_success = c.bind()
            last_auth_err = c.result
            if auth_success:
                break
                
        if not auth_success:
            logger.debug("sessionsmanager - %s" % last_auth_err)
            
        return auth_success
         
    def run(self):
        """run thread"""
        while self.running:
            self.event.wait(self.expire)
            if self.running:
                self.lock.acquire()
                
                expired_sess = []
                for (sess, user) in self.sessions.items():
                    t = time.time()
                    max_age = user['last-activity'] + self.lease
                    if t > max_age:
                        expired_sess.append(sess)

                # delete sessions
                for sess in expired_sess:
                    del self.sessions[sess]
                    
                del expired_sess[:]
                
                self.lock.release()
                
    def stop(self):
        """stop the thread"""
        self.lock.acquire()
        self.running = False
        self.event.set()
        self.lock.release()

SessMngr = None

def del_session(sess_id):
    """delete session"""
    instance().delete_session(sess_id=sess_id)
    
def get_session(sess_id):
    """get session"""
    return instance().get_sesssion(sess_id=sess_id)
    
def do_session_auth(login, password):
    """do session auth"""
    return instance().do_session_auth(login=login,
                                      password=password)
                                      
def do_basic_auth(auth):
    """do basic auth"""
    return instance().do_basic_auth(auth=auth)
    
def instance():
    """returns the singleton"""
    global SessMngr
    return SessMngr
    
def initialize():
    """instance creation"""
    global SessMngr
    SessMngr = SessionsManager()
    
def finalize():
    """destruction of the singleton"""
    global SessMngr
    if SessMngr:
        SessMngr.stop()
        SessMngr.join()
        SessMngr = None