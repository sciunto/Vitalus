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
import psutil
#import signal
import logging, logging.handlers
import sys

from Vitalus.job import Job, TARGETError
import Vitalus.info as info

class Vitalus:
    """
    Class for backups

    :params log_path: directory for logs and database
    """
    def __init__(self, log_path='~/.backup'):
        #Variables

        self.jobs = []
        self.terminate = False

        self.destination = None

        #Logging
        self.backup_log_dir = os.path.expanduser(log_path)
        if not os.path.isdir(self.backup_log_dir):
            os.makedirs(self.backup_log_dir)
        self.pidfilename = os.path.join(self.backup_log_dir, 'backup.pid')

        self.logger = logging.getLogger('Vitalus')
        LOG_PATH = os.path.join(self.backup_log_dir, 'backup.log')
        #hdlr = logging.FileHandler(os.path.join(self.backup_log_dir, 'backup.log'))

        # Add the log message handler to the logger
        log_rotator = logging.handlers.TimedRotatingFileHandler(LOG_PATH, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        log_rotator.setFormatter(formatter)
        self.logger.addHandler(log_rotator)
        
        self.logger.setLevel(logging.INFO)

        #Priority 
        self._set_process_low_priority()

        self.logger.info('Vitalus %s starts...' % info.VERSION)
        #signal.signal(signal.SIGTERM, self._signal_handler)

    def set_log_level(self, level='INFO'):
        """
        Set the logger level (INFO, CRITICAL, DEBUG, ERROR, FATAL)

        :param level: Loger level
        """
        if level == 'INFO':
            self.logger.setLevel(logging.INFO)
            self.logger.info('Set logger level: %s', level)
        elif level == 'CRITICAL':
            self.logger.setLevel(logging.CRITICAL) 
            self.logger.info('Set logger level: %s', level)
        elif level == 'DEBUG':
            self.logger.setLevel(logging.DEBUG)   
            self.logger.info('Set logger level: %s', level)
        elif level == 'ERROR':
            self.logger.setLevel(logging.ERROR)   
            self.logger.info('Set logger level: %s', level)
        elif level == 'FATAL':
            self.logger.setLevel(logging.FATAL)
            self.logger.info('Set logger level: %s', level)
        else:
            self.logger.ERROR('Unknown level')
            


#    def _signal_handler(self, signal, frame):
#        self.logger.warning('Signal received %s', signal)
#        self._set_process_high_priority()
#        self.terminate = True

    def _create_pidfile(self):
        """ Create a pidfile """
        if os.access(self.pidfilename, os.F_OK):
            #Oh oh, there is a lock file
            pidfile = open(self.pidfilename, "r")
            pidfile.seek(0)
            old_pd = pidfile.readline()
            #PID is running?
            if os.path.exists("/proc/%s" % old_pd):
                #Yes
                self.logger.info('An instance is already running, exiting')
                sys.exit(0)
            else:
                #No
                self.logger.info('Removing old PID file')
                os.remove(self.pidfilename)

        with open(self.pidfilename, "w") as pidfile:
            pidfile.write("%s" % os.getpid())


    def _release_pidfile(self):
        """ Release the pidfile """
        self.logger.debug('Removing this PID file')
        os.remove(self.pidfilename)

    def _set_process_high_priority(self):
        """ Change nice/ionice"""
        self.logger.debug('Set high priority')
        #ionice
        p = psutil.Process(os.getpid())
        p.set_ionice(psutil.IOPRIO_CLASS_NONE, value=0)
        #nice
        p.nice = 10

    def _set_process_low_priority(self):
        """ Change nice/ionice"""
        self.logger.debug('Set low priority')
        #ionice
        p = psutil.Process(os.getpid())
        p.set_ionice(psutil.IOPRIO_CLASS_IDLE)
        #nice
        p.nice = 15

    def set_destination(self, destination): 
        """ Set the destination of the backup
        
        :param destination: path
        """        
        self.logger.debug("Set destination: %s", destination)
        self.destination = destination

    #TODO: filter -> *filter ?
    def add_job(self, name, source, period=24, history=False, duration=50, keep=10, filter=None):
        """ Add a new job 
        :param name: backup label
        :param source: backup from...
        :param destination: backup to...
        :param period: min time (hours) between backups
        :param history: Activate snapshots (Boolean)
        :param duration: How many days snapshotss are kept
        :param keep: How many snapshots are (at least) kept
        :param filter: filter, must be a tuple

        Note: filter syntax is the same of rsync. See "FILTER RULES" section
        in the rsync man page.
        """
        if self.destination:
            period_in_seconds = period * 3600
            self.logger.debug("add job: %s", name) 
            try: 
                self.jobs.append(Job(self.backup_log_dir, name, source, 
                    self.destination, period_in_seconds, history, duration, keep, filter))
            except TARGETError:
                #We abort
                pass


    def run(self):
        """ Run all jobs """
        self._create_pidfile()
        for job in self.jobs:
            job.run()
        self._release_pidfile()
        self.logger.info('The script exited gracefully')

if __name__ == '__main__':
    #An example...
    b = Vitalus()
    b.set_log_level('DEBUG')
    b.set_destination('/tmp/sauvegarde')
    #TODO Check that job names are uniq
    b.add_job('test', '/home/gnu/tmp/firefox', period=0.0, history=True)
    b.add_job('test2', '/home/gnu/tmp/debian', period=0.0, history=True)
    b.add_job('test3', '/home/gnu/tmp/photos', period=0.001, history=False)
    b.add_job('test4', '/home/gnu/tmp/www', period=0, history=True)

    b.run()
    
