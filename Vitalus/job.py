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

import os
import re
#import psutil
import shelve
import subprocess
import shutil
import Vitalus.utils as utils
import datetime
import logging
from contextlib import closing
import socket


class TARGETError(Exception):
    """
    Exception for target validity

    :param message: Message
    :type message: string
    """
    def __init__(self, message=''):
        Exception.__init__(self, message)


class Target:
    """
    A target is a source or a destination.
    Both of them can be a local directory
    or a distant one though SSH

    :param target: a target
    :type target: string
    """
    def __init__(self, target):
        # Here, we do not check that path exists.
        # It is checked in check_availability()
        self.logger = logging.getLogger('Vitalus.Target')
        self.logger.debug("Read target %s", target)
        self.target = target
        self.ttype = self._detect_target_type()

        if self.is_local():
            self.path = target
        elif self.is_ssh():
            self.login, self.path = target.split(':')
            self.domain = self.login.split('@')[1]
        if self.path is None:
            raise TARGETError("The path is not correct in %s" % self.target)

    def is_local(self):
        """
        Check if the target is a directory

        :returns: bool -- True if it is a directory
        """
        if self.ttype == 'LOCAL':
            return True
        else:
            return False

    def is_ssh(self):
        """
        Check if the target is a 'SSH' host

        :returns: bool -- True if it is a SSH host
        """
        if self.ttype == 'SSH':
            return True
        else:
            return False

    def check_availability(self):
        """
        Check if the target is available
        For SSH host, it means it's reachable

        :raises: TARGETError -- if not available
        """
        if self.ttype == 'SSH':
            # TODO; here we check the connection.
            # We may check also the filepath
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((self.domain, 22))
            except socket.error:
                raise TARGETError("SSH target %s unreachable" % self.target)
        elif self.ttype == 'LOCAL':
            if not os.path.exists(self.path):
                raise TARGETError("Local target %s unreachable" % self.target)

    def _detect_target_type(self):
        """
        Return the target type
        SSH if matches name@domaine.tld:dir
        LOCAL if it's a directory
        """
        #if re.match('[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]+\:.*', self.target):
        if re.match('[a-zA-Z0-9+_\-\.]+@[a-zA-Z0-9+_\-\.]+\:.*', self.target):
            #ssh
            self.logger.debug("The target %s looks like SSH", self.target)
            return 'SSH'
        else:
            self.logger.debug("The target %s looks like LOCAL", self.target)
            return 'LOCAL'


class Job():
    """
    Class containing a job

    :param log_dir: Log directory path
    :type log_dir: string
    :param destination: Destination path
    :type destination: string
    :param name: Job name
    :type name: string
    :param source: Source path
    :type source: string
    :param period: Min duration between two backups (in seconds)
    :type period: float


    .. note::

        ---
    """

    def __init__(self, log_dir, destination, name, source, period):

        self.name = name
        self.source = Target(source)
        self.destination = Target(destination)
        self.period = period

        self.now = datetime.datetime.now()
        self.current_date = self.now.strftime("%Y-%m-%d_%Hh%Mm%Ss")

        self.backup_log_dir = log_dir

        self.logger = logging.getLogger('Vitalus.Job')

        #Logs specific to the rsync job
        job_log = os.path.join(self.backup_log_dir, self.name + '.log')
        self.job_logger = logging.getLogger(self.name)
        log_rotator = logging.handlers.TimedRotatingFileHandler(job_log, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        self.job_logger.addHandler(log_rotator)
        self.job_logger.setLevel(logging.INFO)

        #Set previous and current backup paths
        self.previous_backup_path = None  # will be detected later
        self.current_backup_path = None

    def _set_lastbackup_time(self):
        """
        Set the last backup (labeled name) time
        """
        self.logger.debug('Set lastbackup time')
        with closing(shelve.open(os.path.join(self.backup_log_dir, 'time.db'))) as timebase:
            timebase[self.name] = datetime.datetime.now()

    def _check_need_backup(self):
        """
        Return True if backup needed
        False otherwise

        :returns: bool
        """
        self.logger.debug("Check time between backups for %s", self.name)
        with closing(shelve.open(os.path.join(self.backup_log_dir, 'time.db'))) as timebase:
            try:
                last = timebase[self.name]
            except KeyError:
                #Not yet stored
                #Run the first backup
                self.logger.debug("%s: first backup", self.name)
                return True

        #Calculate the difference
        self.logger.debug("now= %s", datetime.datetime.now())
        self.logger.debug("last= %s", last)
        diff = datetime.datetime.now() - last
        difftime = diff.total_seconds()
        self.logger.debug("diff= %s seconds", difftime)
        self.logger.debug("period= %s seconds", self.period)
        if difftime > self.period:
            self.logger.debug("%s need backup", self.name)
            return True
        else:
            self.logger.debug("%s does not need backup", self.name)
            return False

    def run(self, uid=None, gid=None):
        """
        Run the job.
        """
        self.logger.debug('Start job: %s', self.name)
