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

REPO_SNIPPETS = 0
REPO_ACTIONS = 1
REPO_WORKSPACES = 2

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

ROLE_LIST = [
    ROLE_ADMIN,
    ROLE_OPERATOR
]

ERROR = 500
NOT_FOUND = 404
FORBIDDEN = 403
FAILED = 400
OK = 200
ALREADY_EXISTS = 412

STATE_WAITING = 'WAITING'
STATE_RUNNING = 'RUNNING'
STATE_FAILURE = 'FAILURE'
STATE_SUCCESS = 'SUCCESS'

SNIPPET_CREATED = 0
SNIPPET_STARTED = 1
SNIPPET_TERMINATED = 2

NOTIFY_START = "start"
NOTIFY_DONE = "done"
NOTIFY_FAILURE = "failure"

RETCODE_PASS = 0
RETCODE_ERROR = 3

RETCODE_LIST = {
                RETCODE_PASS: STATE_SUCCESS,
                RETCODE_ERROR: STATE_FAILURE
               }

SCHED_NOW = 0
SCHED_AT = 1 
SCHED_HOURLY = 2
SCHED_DAILY = 3
SCHED_WEEKLY = 4
SCHED_EVERY_X = 5

SCHED_MODE = [
                SCHED_NOW,
                SCHED_AT,
                SCHED_HOURLY,
                SCHED_DAILY,
                SCHED_WEEKLY,
                SCHED_EVERY_X
             ]