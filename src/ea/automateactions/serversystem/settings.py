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

import sys
import os
import json
import yaml

n = os.path.normpath
cfg = None  # singleton
       
def get_app_path():
    file_path = os.path.dirname(os.path.abspath(__file__))
    app_path = os.sep.join(file_path.split(os.sep)[:-1])
    return n(app_path)
    
def save():
    """save settings"""
    global cfg

    # checking if the file exists
    config_file = '%s/data/config.yml' % (get_app_path())
    if not os.path.isfile(n(config_file)):
        raise Exception("yaml config file doesn't exist in data/")

    try:
        cfg_str = yaml.safe_dump(cfg)
    except Exception as e:
        raise Exception("dump config error: %s" % e)

    with open(config_file, 'w') as fd:
        fd.write(cfg_str)


def initialize():
    """initialize"""
    global cfg
    
    # checking if the file exists
    config_file = '%s/data/config.yml' % (get_app_path())
    if not os.path.isfile(n(config_file)):
        raise Exception("yaml config file doesn't exist in data/")

    # load yaml
    with open(config_file, 'r') as fd:
        cfg_str = fd.read()

    try:
        cfg = yaml.safe_load(cfg_str)
    except Exception as e:
        raise Exception("bad yaml config file provided: %s" % e)

def finalize():
    """finalize"""
    global cfg
    if cfg:
        cfg = None