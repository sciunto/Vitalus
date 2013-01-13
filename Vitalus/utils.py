#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>
#
# Author: Francois Boulogne <fboulogne at sciunto dot org>, 2012

import tarfile
import os.path
import logging
import datetime

logger = logging.getLogger('Vitalus.utils')


def compress(path):
    """ Compress the directory """

    head, tail = os.path.split(path)
    archive = str(path) + '.bz2'
    tar = tarfile.open(archive, "w:bz2")
    tar.add(path, arcname=tail)
    tar.close()


def get_folder_size(path):
    """
    Get the size of the content in path
    """
    size = 0
    for item in os.walk(path):
        for file in item[2]:
            try:
                size += os.path.getsize(os.path.join(item[0], file))
            except:
                logger.error("Impossible to get size of: %s",
                    os.path.join(item[0], file))
    return size


def get_last_file(file_list):
    """
    Return the more recent file in a list (in the format "%Y-%m-%d_%Hh%Mm%Ss")

    :param file_list: list of files

    :return: filename
    """
    if file_list == []:
        return None

    last_date = datetime.datetime(1, 1, 1, 0, 0)
    last = None
    for afile in file_list:
        try:
            date = datetime.datetime.strptime(afile, '%Y-%m-%d_%Hh%Mm%Ss')
        except ValueError:
            continue
        if date > last_date:
            last_date = date
            last = afile
    return last


def get_older_files(file_list, days=5, keep=10):
    """
    Return older files in a list but keep a minium amount of files

    :param file_list: list of files named in the format "%Y-%m-%d_%Hh%Mm%Ss"
    :param days: files older than this value are old
    :param keep: keep at least this number of files

    :returns: a sorted list of old files
    """

    if (days < 0) or (keep < 0):
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
    #While we remove too much,
    #re-feed keep array
    while (len(recent) < keep) and (old != []):
        recent.append(old.pop(-1))

    return old
