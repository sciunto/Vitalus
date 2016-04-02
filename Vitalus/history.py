#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
# Author: Francois Boulogne <fboulogne at sciunto dot org>, 2012

import os.path
import logging
import datetime

logger = logging.getLogger('Vitalus.history')


def older(file_list, days=5):
    """
    Return older files than "days"

    :param file_list: list of files named in the format "%Y-%m-%d_%Hh%Mm%Ss"
    :param days: files older than this value are old

    :returns: a sorted list of old files
    """
    if days < 0:
        raise ValueError

    now = datetime.datetime.now()

    old = []
    recent = []
    for afile in file_list:
        try:
            date = datetime.datetime.strptime(afile, '%Y-%m-%d_%Hh%Mm%Ss')
        except ValueError:
            continue
        if (now - date) >= datetime.timedelta(days):
            old.append(afile)
        else:
            recent.append(afile)

    old.sort()
    return old
