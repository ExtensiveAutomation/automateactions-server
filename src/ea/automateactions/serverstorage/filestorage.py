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
import time 

from ea.automateactions.serverengine import constant
from ea.automateactions.serversystem import logger
from ea.automateactions.serversystem import settings

class FilesStorage():
    """files storage"""
    def __init__(self, repo_path):
        """repstorageository class"""
        self.repo_path = repo_path

    def get_path(self, workspace, filename=""):
        """get repo path"""
        p = self.repo_path % workspace
        p = "%s/%s" % (p,filename)
        return os.path.normpath(p)

    def add(self, item_path, workspace, user, content_file):
        """add file"""
        # checking if the file requested exists
        file_path = self.get_path(filename=item_path,
                                  workspace=workspace)

        # prevent directory traversal
        if not file_path.startswith(self.get_path(workspace=workspace)):
            return (constant.FORBIDDEN, 'access denied')

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w") as fh:
            fh.write(content_file)

        return (constant.OK, "success" )

    def duplicate(self, item_path, workspace, user):
        """duplicate file or folder"""
        # checking if the file requested exists
        full_path = self.get_path(filename=item_path,
                                  workspace=workspace)
        if not os.path.exists(full_path):
            return (constant.NOT_FOUND, '(%s) does not exits' % item_path)

        # is a file or folder ?
        if os.path.isfile(full_path):
            return self.duplicate_file(file_path=full_path)
        
        return self.duplicate_folder(folder_path=full_path)

    def duplicate_file(self, file_path):
        """duplicate file"""
        base_dir = os.path.dirname(file_path)
        base_file = os.path.basename(file_path)

        random_name = hex(int(time.time() * 10000000))[2:]
        new_path = "%s/%s-COPY#%s" % (base_dir, base_file, random_name)
        new_path = os.path.normpath(new_path)

        shutil.copy(file_path, new_path)

        return (constant.OK, "success")

    def duplicate_folder(self, folder_path):
        """duplicate folder"""
        
        if folder_path.endswith("/"):
            folder_path = folder_path[:-1]

        random_name = hex(int(time.time() * 10000000))[2:]
        new_path = "%s-COPY#%s" % (folder_path, random_name)
        new_path = os.path.normpath(new_path)

        shutil.copy(folder_path, new_path)

        return (constant.OK, "success")

    def update(self, item_path, workspace, new_name, user):
        """update file or folder"""
        # checking if the file or folder requested exists
        full_path = self.get_path(filename=item_path,
                                  workspace=workspace)
        if not os.path.exists(full_path):
            return (constant.NOT_FOUND, '(%s) does not exits' % item_path)

        # is a file or folder ?
        if os.path.isfile(full_path):
            return self.update_file_name(file_path=full_path, new_name=new_name)
        
        return self.update_folder_name(folder_path=full_path, new_name=new_name)

    def update_file_name(self, file_path, new_name):
        """update file name"""

        base_dir = os.path.dirname(file_path)

        new_path = "%s/%s" % (base_dir, new_name)
        new_path = os.path.normpath(new_path)

        os.rename(file_path, new_path)

        return (constant.OK, "success")

    def update_folder_name(self, folder_path, new_name):
        """update folder name"""

        if folder_path.endswith("/"):
            folder_path = folder_path[:-1]

        base_dir = os.path.dirname(folder_path)

        new_path = "%s/%s" % (base_dir, new_name)
        new_path = os.path.normpath(new_path)

        os.rename(folder_path, new_path)

        return (constant.OK, "success")

    def delete(self, item_path, workspace, user):
        """delete item"""
        # checking if the file requested exists
        full_path = self.get_path(filename=item_path,
                                  workspace=workspace)
        if not os.path.exists(full_path):
            return (constant.NOT_FOUND, '(%s) does not exits' % item_path)

        # is a file or folder ?
        if os.path.isfile(full_path):
            return self.delete_file(file_path=full_path)
        
        return self.delete_folder(folder_path=full_path)

    def delete_file(self, file_path):
        """delete file"""
        # delete file
        os.remove(file_path)
        
        return (constant.OK, "success")

    def delete_folder(self, folder_path):
        """delete folder"""
        # delete folder and all inside
        shutil.rmtree(folder_path)
        
        return (constant.OK, "success")

    def read_file(self, filename, workspace, user):
        """read file"""
        # checking if the file requested exists
        full_path = self.get_path(filename=filename,
                                  workspace=workspace)
        if not os.path.exists(full_path):
            return (constant.NOT_FOUND, 'file (%s) does not exits' % filename)

        with open(full_path, "r") as fh:
            file_raw = fh.read()

        return (constant.OK, {"file": { "content": file_raw } } )

    def get_files(self, workspace, user):
        """get a listing of all files"""
        # recursive call to get all files
        full_path = self.get_path(workspace=workspace)
        if not os.path.exists(full_path):
            return (constant.NOT_FOUND, 'workspace does not exits')
            
        listing = self.recursive_listing(folder_path=full_path,
                                         parent_id="00")

        return (constant.OK, listing)
        
    def recursive_listing(self, folder_path, parent_id):
        """recursive function to list all files"""
        i = 0
        listing = {}
        for entry in list(os.scandir(folder_path)):
            # parse folders
            if entry.is_dir(follow_symlinks=False):
                if entry.name.startswith("."):
                    continue

                i += 1
                listing["%s%s" % (parent_id, i)] = {"type": "folder",
                                                    "name": entry.name,
                                                    "parent-id": "%s" % parent_id}

                new_listing = self.recursive_listing(folder_path=entry.path,
                                                     parent_id="%s%s" % (parent_id,
                                                                         i))
                listing.update(new_listing)

            # parse files
            else:
                if entry.name.startswith("."):
                    continue

                i += 1
                file_name, file_ext = os.path.splitext(entry.name)
                file_ext = file_ext[1:]
                listing["%s%s" % (parent_id, i)] = {"type": "file",
                                                    "name": file_name,
                                                    "parent-id": "%s" % parent_id,
                                                    "extension": file_ext}

        return listing
