#!/usr/bin/python

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

"""cli usage for the server"""

from optparse import OptionParser
import sys

from ea.automateactions.serverengine import coreserver
from ea.automateactions.servercontrol import cliserver

# prepare the command line with all options
parser = OptionParser()
parser.set_usage("./automateactions.py "
                 "[start|stop|status|reload|version]")

parser.add_option('--start', dest='start',
                  default=False,
                  action='store_true',
                  help="Start the server.")
parser.add_option('--version',
                  dest='version',
                  default=False,
                  action='store_true',
                  help='Show the version.')
parser.add_option('--stop', dest='stop',
                  default=False,
                  action='store_true',
                  help="Stop the server.")
parser.add_option('--status', dest='status',
                  default=False,
                  action='store_true',
                  help='Show the current status of the server.')
parser.add_option('--reload',
                  dest='reload',
                  default=False,
                  action='store_true',
                  help='Reload the configuration of the server.')

                  
(options, args) = parser.parse_args()


def cli():
    """basic cli to control the server"""
    coreserver.initialize()
    cliserver.initialize(coreserver=coreserver.instance())
    
    if options.stop is True:
        coreserver.stop()
        sys.exit(0)

    if options.status is True:
        coreserver.status()
        sys.exit(0)

    if options.reload is True:
        cliserver.reload_configuration()
        sys.exit(0)

    if options.start is True:
        coreserver.start()
        sys.exit(0)

    if options.version is True:
        cliserver.version()
        sys.exit(0)

    parser.print_help()
    sys.exit(2)
