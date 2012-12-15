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


class TARGETError(Exception):
    """
    Exception for target validity
    :param message: Message
    """
    def __init__(self, message=''):
        Exception.__init__(self, message)

import os
import re
import psutil
import shelve
import subprocess
import shutil
import Vitalus.utils as utils
import datetime
import logging
from contextlib import closing

class Job:
    """
    Class containing a job

    :param min_disk_space: minimal disk space
    :param log_dir: Log directory path
    :param name: Job name
    :param source: Source path
    :param destination: Destination path
    :param period: Min duration between two backups (in seconds)
    :param snapshot: Activate snapshots (Boolean)
    :param duration: How many days snapshots are kept
    :param keep: How many snapshots are (at least) kept
    :param filter: Rsync filters
    """
    #TODO signal...

    def __init__(self, log_dir, name, source, destination, period, snapshot, duration, keep, filter):
       
        self.name = name
        self.source = source
        self.destination = destination
        self.period = period
        self.snapshot = snapshot
        self.duration = duration
        self.keep = keep
        self.filter = filter

        self.now = datetime.datetime.now()
        self.current_date = self.now.strftime("%Y-%m-%d_%Hh%Mm%Ss")

        self.backup_log_dir = log_dir
        
        self.logger = logging.getLogger('Vitalus.Job') #TODO add the job name in the format
        
        #Logs specific to the rsync job
        job_log = os.path.join(self.backup_log_dir, self.name + '.log')
        self.job_logger = logging.getLogger(self.name)
        log_rotator = logging.handlers.TimedRotatingFileHandler(job_log, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        self.job_logger.addHandler(log_rotator)
        self.job_logger.setLevel(logging.INFO)
        self.job_logger.info('='*20 + str(self.now) + '='*20)
        
        #Source types
        self.source_type = self._get_target_type(self.source)
        self.dest_type = self._get_target_type(self.destination)

        self._check_disk_usage()

    def _get_target_type(self, target):
        """
        Return the target type
        SSH if matches name@domaine.tld:dir
        DIR if it's a directory
       
        :param target: Target (source or destination)
        :raises TARGETError: weird target type 
        """
        if re.match('[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]+\:.*', target):
            #ssh
            self.logger.debug('The target looks like SSH')
            return 'SSH'
        else:
            if not os.path.exists(target):
                self.logger.warn("The target %s does not exist", target)
                self.logger.info('Aborting...')
                raise TARGETError("Target %s does not exist" % target)
            else:
                self.logger.debug('The target looks like DIR')
                return 'DIR'

    def _check_disk_usage(self):
        """
        Check the disk usage
        :raises TARGETError: if low disk space
        """
        if self.dest_type == 'DIR':
            #TODO, change the criterion
            pass
            #if psutil.disk_usage(self.destination)[2] < utils.get_folder_size(self.source): 
            #    self.logger.critical("Low disk space: %s", self.destination)
            #    raise TARGETError('Low disk space on %s' % self.destination)
        elif self.dest_type == 'SSH':
            #TODO
            pass

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

    def _delete_old_files(self, path, days=10, keep=10): 
        """
        Delete old archives in a path

        :param path: path to clean
        :param days: delete files older than this value
        :param keep: keep at least this amount of archives
        """
        #TODO : review logs

        ####if self.terminate: return
        filenames = [os.path.join(path, el) for el in os.listdir(path) ]
        #delete first the older one
        filenames.sort() #newer first
        nb_archives = len(filenames)
        for filepath in enumerate(filenames):
            #keep a sufficient number of archives
            if (nb_archives - filepath[0]) <= keep:
                self.logger.debug('nb archives %s, keep %s, archive %s' % (nb_archives, keep, filepath[0]))
                return
            #Are they too old?
            file_date = datetime.datetime.fromtimestamp(os.path.getmtime(filepath[1]))
            if datetime.datetime.now() - file_date > datetime.timedelta(days=days): 
                self.logger.info("remove %s", filepath[1])
                shutil.rmtree(filepath[1]) #FIXME: raise something?
                #try:
                #    os.remove(filepath[1])
                #except OSError:
                #    self.logger.warn("Impossible to remove %s", filepath[1])

            else:
                self.logger.debug("keep %s", filepath[1])
                return

    def _get_last_backup(self, path):
        """
        Get the last backup in path
        Return None if not available

        :param path: path to look at
        """
        #TODO : SSH look via ssh
        if not os.path.isdir(path):
            return None
        filenames = [os.path.join(path, el) for el in os.listdir(path)]
        filenames.sort()
        if filenames == []:
            return None
        return filenames[-1] 

    def _prepare_destination(self): 
        """
        Prepare the destination to receive a backup:
        * create dirs
        * Initialize paths
        """
        self.previous_backup_path = None
        self.current_backup_path = None

        if self.dest_type != 'SSH':
            if self.snapshot:
                last_date = self._get_last_backup(os.path.join(self.destination, self.name))
                if last_date is None:
                    #It means that this is the first backup.
                    self.previous_backup_path = None
                else:
                    self.previous_backup_path = os.path.join(self.destination, self.name, str(last_date))
                self.current_backup_path = os.path.join(self.destination , self.name, str(self.current_date))
                os.makedirs(self.current_backup_path) #This one does not exist!
            else:
                self.current_backup_path = os.path.join(self.destination, self.name)
                try:
                    os.makedirs(self.current_backup_path) #This one may exist!
                except OSError:
                    #they could already exist
                    pass
        else:
            # Create dirs on the server
            login, dest_dir_path = destination.split(':')
            #add ~/ if does not start with /
            if not dest_dir_path.startswith('/'):
                dest_dir_path = os.path.join('~', dest_dir_path)
            if self.snapshot:
                #For the moment, we do not support snapshots via SSH
                pass
            else:
                self.current_backup_path = os.path.join(dest_dir_path, self.name)

            #Create dirs
            command = ['ssh', '-t', login, 'mkdir', '-p', self.current_backup_path]
            self.logger.debug('SSH mkdir command: ' + str(command))
            process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            self.logger.debug('SSH mkdir result: ' + stdout.decode())
                
        self.logger.debug("Previous backup path: %s", self.previous_backup_path)
        self.logger.debug("Current backup path: %s", self.current_backup_path)


    def _prepare_rsync_command(self): 
        """
        Compose the rsync command
        """
        command = list()
        command.append('/usr/bin/rsync')

        # a: archive (recursivity, preserve rights and times...)
        # v: verbose
        # h: human readable
        # stat: file rate stats
        # delete: delete extraneous files from dest dirs
        # delete-excluded: also delete excluded files from dest dirs
        command.append('-avh') 
        command.append('--stats')
        command.append('--delete')
        command.append('--delete-excluded')

        # z: compress the flux if transfert thought a network
        if (self.source_type or self.dest_type) == 'SSH':
            command.append('-z')
        else: #FIXME for the moment, no snapshots though SSH !
            # link-dest: write snapshots with hard-links
            if self.snapshot and self.previous_backup_path is not None:
                command.append('--link-dest=' + self.previous_backup_path)

        # Add source and destination
        command.append(self.source)
        command.append(self.current_backup_path)

        if self.filter:
            # Add filters, the resulting command must look like
            # rsync -av a b --filter='- *.txt' --filter='- *dir'
            for element in self.filter:
                command.append('--filter=' + element)
                self.logger.debug("add filter: %s", element)
                
        self.logger.debug("rsync command: %s", command)
        return command

#    def _compress_increments(self):
#        """
#        Compress increments and delete old ones
#        """
#        if self.dest_type == 'DIR':
#            #compress if not empty
#            if os.listdir(self.inc_path) != []:
#                self.logger.debug("Zip the directory: %s", self.inc_path)
#                utils.compress(self.inc_path)
#            else:
#                self.logger.info('Empty increment')
#                pass
#            #delete the dir (we keep only non-empty tarballs
#            shutil.rmtree(self.inc_path)
#
#            #MrProper: remove old tarballs
#            self._delete_old_files(self.inc_dir, days=self.duration, keep=self.keep)
#        elif self.dest_type == 'SSH':
#            pass
#            #TODO ! compress dir though ssh
#            #TODO Remove old dirs though ssh

    def _rsync(self):
        """ 
        Run rsync to do the task.
        """
        command = self._prepare_rsync_command()

        #If a signal is received, stop the process
        #if self.terminate: return

        #Run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        #Dump outputs in log files
        log = stdout.decode()
        self.job_logger.info(log)

        if stderr != b'':
            self.job_logger.info('Errors:')
            self.job_logger.info(stderr.decode())

    def run(self):
        """
        Run the job
        """
        if self._check_need_backup():
            print(self.name)
            self.logger.info("Backup %s", self.name)
            #Prepare the destination
            self._prepare_destination()
            self.logger.debug("source path %s", self.source) 
            self.logger.debug("destination path %s", self.destination) 
            self.logger.debug("filter path %s", self.filter)
            #Run rsync
            self._rsync()
            #Compress
            #Job done, update the time in the database
            self._set_lastbackup_time()
        #Remove old snapshots, local only
        if self.dest_type == 'DIR' and self.snapshot:
            dest = os.path.join(self.destination, self.name)
            self._delete_old_files(dest, days=self.duration, keep=self.keep)
            #Symlink
            last = os.path.join(self.destination , self.name, 'last')
            if os.path.islink(last):
                os.remove(last)
            try:
                os.symlink(self.current_backup_path, last)
            except FileExistsError:
                self.logger.warn('The symlink %s could not be created because a file exists', last)
            except AttributeError:
                self.logger.warn('Attribute error for symlink') #FIXME


