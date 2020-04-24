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

import logging
import logging.handlers

LG = None  # Singleton

def instance():
    """Returns Singleton"""
    return LG

def info(txt):
    """Log info message"""
    global LG
    LG.info(txt)

def error(txt):
    """Log error message"""
    global LG
    LG.error(txt)

def debug(txt):
    """Log trace message"""
    global LG
    LG.debug(txt)

def initialize(log_file, level, max_size, nb_files):
    """initialize"""
    global LG
    LG = logging.getLogger('Logger')
    
    set_level(level=level)
    
    max_bytes = int(max_size.split('M')[0]) * 1024 * 1024
    
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   maxBytes=int(max_bytes),
                                                   backupCount=int(nb_files) )
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    LG.addHandler(handler)
    
def set_level(level):
    """set the level log"""
    global LG
    
    # write everything messages
    if level == 'DEBUG':
        LG.setLevel(logging.DEBUG)
        
    # write anything that is an error or worse.
    if level == 'ERROR':
        LG.setLevel(logging.ERROR)
        
    # write anything that is an info message or worse.
    if level == 'INFO':
        LG.setLevel(logging.INFO)
        
def finalize():
    """Destroy Singleton"""
    global LG
    if LG:
        logging.shutdown()
        LG = None