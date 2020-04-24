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
import hashlib
from binascii import hexlify

from ea.automateactions.serverengine import constant
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings

n = os.path.normpath

class UsersManager:
    """users manager"""
    def __init__(self):
        """class init"""
        self.cache = []

        self.load_users()
        self.gensalt()
        self.genpass_api()

    def gensalt(self):
        """generate salt"""
        if settings.cfg['security']["salt"] is None:
            logger.debug("sessionsmanager - generate salt")
            settings.cfg['security']["salt"] = hexlify(os.urandom(20)).decode("utf8")
            settings.save()

            # generate hash password for all users
            self.genpass_session()

    def genpass_api(self):
        """generate basic secret if not provided"""
        new_secrets = False
        for u in self.cache["users"]:
            (login, p) = list(u.items())[0]
            if p["secrets"]["basic"] is None:
                logger.debug("sessionsmanager - generate password api for user=%s" % login)
                api_secret = hexlify(os.urandom(20)).decode("utf8")

                p["secrets"]["basic"] = api_secret
                new_secrets = True

        # save changes to file
        if new_secrets:
            self.save_users()

    def genpass_session(self):
        """generate session hash secret if the salt was generated"""
        
        for u in self.cache["users"]:
            # { "login": { "role": ..., "secrets": {...} } }
            login = list(u.keys())[0]

            logger.debug("sessionsmanager - generate password session for user=%s" % login)
            u[login]["secrets"]["session"] = self.genpass_hash(password=u[login]["secrets"]["session"])

        # save changes to file
        self.save_users()

    def genpass_hash(self, password):
        """generate password hash"""
        # create a sha512 hash with salt: sha512(salt + sha512(password))
        pwd_hash = hashlib.sha512()
        pwd_hash.update(password.encode("utf8"))
        
        pwd_salt = "%s%s" % (settings.cfg['security']["salt"], pwd_hash.hexdigest())

        pwdsalt_hash = hashlib.sha512()
        pwdsalt_hash.update(pwd_salt.encode('utf-8'))

        return pwdsalt_hash.hexdigest()

    def save_users(self):
        """save users to yaml file"""
        # checking if the file exists
        users_file = '%s/data/users.yml' % (settings.get_app_path())
        if not os.path.isfile(n(users_file)):
            raise Exception("yaml users file doesn't exist in data/")

        try:
            usrs_str = yaml.safe_dump(self.cache)
        except Exception as e:
            raise Exception("dump users error: %s" % e)

        with open(users_file, 'w') as fd:
            fd.write(usrs_str)
            
    def load_users(self):
        """load users from yaml file"""
        users_file = '%s/data/users.yml' % (settings.get_app_path())
        if not os.path.isfile(n(users_file)):
            raise Exception("yaml users file doesn't exist in data/")

        # load yaml
        with open(users_file, 'r') as fd:
            usrs_str = fd.read()

        try:
            self.cache = yaml.safe_load(usrs_str)
        except Exception as e:
            raise Exception("bad yaml users file provided: %s" % e)

        logger.debug("usersmanager - users cache "
                     "nb items: %s" % len(self.cache["users"]) )

    def search_user(self, login):
        """search user by login"""
        logger.debug("usersmanager - search in "
                     "cache login=%s" % login)
                     
        found = None
        for u in self.cache["users"]:
            (l, _) = list(u.items())[0]
            if l == login:
                found = u
                break
        return found

    def reset_password(self, login):
        """reset password"""
        logger.debug('usersmanager - reset password '
                     'for user=%s' % login)
        
        # search the user
        u = self.search_user(login=login)
        if u is None:
            error_str = "user=%s does not exist" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.NOT_FOUND, error_str)
            
        # reset password and save changes to file
        u[login]["secrets"]["session"] = self.genpass_hash("")
        self.save_users()

        return (constant.OK, "success")
     
    def get_users(self):
        """get users"""
        logger.debug("usersmanager - get users")

        return (constant.OK, self.cache["users"])
        
    def get_user(self, login):
        """get user"""
        logger.debug("usersmanager - get user=%s" % login)

        # search the user
        u = self.search_user(login=login)
        if u is None:
            error_str = "user=%s does not exist" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.NOT_FOUND, error_str)

        return (constant.OK, [ u ])
       
    def add_user(self, login, password, role):
        """add user"""
        logger.debug('usersmanager - add user with login=%s' % login)
        
        # checking if the login is uniq
        u = self.search_user(login=login)
        if u is not None:
            error_str = "login (%s) already exists" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.ALREADY_EXISTS, error_str)

        # create random key secret for api
        key_secret = hexlify(os.urandom(20)).decode("utf8")
           
        # add user
        new_secrets = { "session": self.genpass_hash(password), "basic": key_secret }
        new_user = { login: { "role": role, "secrets": new_secrets} }
        self.cache["users"].append( new_user )
        
        # save users to file
        self.save_users()

        return (constant.OK, "success")
        
    def update_role(self, login, role):
        """update role user"""
        logger.debug('usersmanager - update role for user=%s' % login)
        
        # search the user
        u = self.search_user(login=login)
        if u is None:
            error_str = "user=%s does not exist" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.NOT_FOUND, error_str)

        # update user in cache and save changes to file
        u[login]["role"] = role
        self.save_users()

        return (constant.OK, "success")
        
    def update_password(self, login, curpass, newpass):
        """update password"""
        logger.debug('usersmanager - update password '
                     'for user=%s' % login)
        
        # search the user
        u = self.search_user(login=login)
        if u is None:
            error_str = "user=%s does not exist" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.NOT_FOUND, error_str)
            
        # check the provided current password
        if self.genpass_hash(curpass) != u[login]["secrets"]['session']:
            logger.error('usersmanager - bad current password '
                         'for user=%s' % login)
            return (constant.FAILED, "bad current password provided")
        
        # update password and save changes to file
        u[login]["secrets"]["session"] = self.genpass_hash(newpass)
        self.save_users()

        return (constant.OK, "success")
     
    def delete_user(self, login):
        """delete user"""
        logger.debug('usersmanager - delete user login=%s' % login)
        
        # search the user
        u = self.search_user(login=login)
        if u is None:
            error_str = "user=%s does not exist" % login
            logger.error('usersmanager - %s' % error_str)
            return (constant.NOT_FOUND, error_str)
            
        # remove from cache
        self.cache["users"].remove(u)
        
        # save users to file
        self.save_users()

        return (constant.OK, "success")
        
UsersMngr = None

def delete_user(login):
    """delete user"""
    return instance().delete_user(login=login)

def update_role(login, role):
    """update role user"""
    return instance().update_role(login=login,
                                  role=role)
                                     
def add_user(login, password, role):
    """add user"""
    return instance().add_user(role=role,
                               login=login,
                               password=password)
        
def get_user(login):
    """get user"""
    return instance().get_user(login=login)

def get_users():
    """get user"""
    return instance().get_users()
        
def update_pwd(login, curpass, newpass):
    """update password"""
    return instance().update_password(login=login,
                                      newpass=newpass,
                                      curpass=curpass)
                                        
def reset_pwd(login):
    """reset password"""
    return instance().reset_password(login=login)
    
def search_user(login):
    """search user by login"""
    return instance().search_user(login=login)

def genpass_hash(password):
    """generate hash password"""
    return instance().genpass_hash(password=password)

def instance():
    """returns the singleton"""
    global UsersMngr
    return UsersMngr
    
def initialize():
    """instance creation"""
    global UsersMngr
    UsersMngr = UsersManager()
    
def finalize():
    """destruction of the singleton"""
    global UsersMngr
    if UsersMngr:
        UsersMngr = None