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
#import psutil
import shelve
import subprocess
import shutil
import Vitalus.utils as utils
import datetime
import logging
from contextlib import closing


class Target:
    """
    A target is a source or a destination.
    Both of them can be a local directory
    or a distant one though SSH
    """
    
    def __init__(self, target):
        self.logger = logging.getLogger('Vitalus.Target') 
        self.logger.debug("Read target %s", target)
        self.target = target
        self.ttype = self._detect_target_type()

        if self.is_dir():
            self.path = target
        elif self.is_ssh():
            self.login, self.path = target.split(':')


    def is_dir(self):
        if self.ttype == 'DIR':
            return True
        else:
            return False

    def is_ssh(self):
        if self.ttype == 'SSH':
            return True
        else:
            return False

    def _detect_target_type(self):
        """
        Return the target type
        SSH if matches name@domaine.tld:dir
        DIR if it's a directory
       
        :param target: Target (source or destination)
        :raises TARGETError: weird target type 
        """
        if re.match('[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]+\:.*', self.target):
            #ssh
            self.logger.debug("The target %s looks like SSH", self.target)
            return 'SSH'
        else:
            if not os.path.exists(self.target):
                self.logger.warn("The target %s does not exist", self.target)
                self.logger.info('Aborting...')
                raise TARGETError("Target %s does not exist" % self.target)
            else:
                self.logger.debug("The target %s looks like DIR", self.target)
                return 'DIR'



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


    Note:
    -----
    Source and destination path can be either real path
    or a ssh login joined to the path by a : caracter.
    """
    #TODO signal...

    def __init__(self, log_dir, name, source, destination, period, snapshot, duration, keep, filter):
       
        self.name = name
        self.source = Target(source)
        self.destination = Target(destination)
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
        
        #Set previous and current backup paths
        self.previous_backup_path = None
        self.current_backup_path = None

        if self.destination.is_dir():
            last_date = self._get_last_backup(os.path.join(self.destination.path, self.name))
            self.current_backup_path = os.path.join(self.destination.path , self.name, str(self.current_date))
            if last_date is None:
                #It means that this is the first backup.
                self.previous_backup_path = None
            else:
                self.previous_backup_path = os.path.join(self.destination.path, self.name, str(last_date))

        elif self.destination.is_ssh():
            #TODO detect previous backup though SSH
            #FOr that, we should refactor get_last_backup

            if self.snapshot:
                #For the moment, we do not support snapshots via SSH
                self.current_backup_path = os.path.join(self.destination.path, self.name, str(self.current_date))
            else:
                self.current_backup_path = os.path.join(self.destination.path, self.name)
            

        self.logger.debug("Previous backup path: %s", self.previous_backup_path)
        self.logger.debug("Current backup path: %s", self.current_backup_path)


#    def _check_disk_usage(self):
#        """
#        Check the disk usage
#        :raises TARGETError: if low disk space
#        """
#        if self.destination.is_dir():
#            #TODO, change the criterion
#            pass
#            #if psutil.disk_usage(self.destination)[2] < utils.get_folder_size(self.source): 
#            #    self.logger.critical("Low disk space: %s", self.destination)
#            #    raise TARGETError('Low disk space on %s' % self.destination)
#        elif self.destination.is_ssh():
#            #TODO
#            pass

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
                try:
                    shutil.rmtree(filepath[1])
                except OSError:
                    self.logger.error("Impossible to delete %s (symlink?)", filepath[1])
            else:
                self.logger.debug("Keep backup %s", filepath[1])
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
        Create dirs
        """
        if self.destination.is_dir():
            if self.snapshot:
                os.makedirs(self.current_backup_path) #This one does not exist!
            else:
                if self.previous_backup_path is None:
                    os.makedirs(self.current_backup_path, exist_ok=True) 
                else:
                    #Move dir to set the new date in the path
                    os.rename(self.previous_backup_path, self.current_backup_path)
        elif self.destination.is_ssh():
            #Create dirs
            command = ['ssh', '-t', self.destination.login, 'mkdir', '-p', self.current_backup_path]
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
        if (self.source.is_ssh() or self.destination.is_ssh()):
            command.append('-z')
        #else: #FIXME for the moment, no snapshots though SSH !
        #    pass
            # link-dest: write snapshots with hard-links
        if self.snapshot and self.previous_backup_path is not None:
            command.append('--link-dest=' + self.previous_backup_path)

        # Add source and destination
        command.append(self.source.target)
        if self.destination.is_ssh():
            full_dest = str(self.destination.login) + ':' + str(self.current_backup_path)
            command.append(full_dest)
        else:
            command.append(self.current_backup_path)

        if self.filter:
            # Add filters, the resulting command must look like
            # rsync -av a b --filter='- *.txt' --filter='- *dir'
            for element in self.filter:
                command.append('--filter=' + element)
                self.logger.debug("add filter: %s", element)
                
        self.logger.debug("rsync command: %s", command)
        return command

    def _run_command(self, command):
        """ 
        Run a command and log stderr+stdout in a dedicated log file.
        :param command: a list, each element is a part of the command line

        Example
        -------
        command = ['/usr/bin/cp', '-r', '/home', '/tmp']
        """

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
        #TODO rewriting and integration
        #self._check_disk_usage()
        if self._check_need_backup():
            self.job_logger.info('='*20 + str(self.now) + '='*20)
            print(self.name)
            self.logger.info("Backup %s", self.name)
            #Prepare the destination
            self._prepare_destination()
            self.logger.debug("source path %s", self.source.target) 
            self.logger.debug("destination path %s", self.destination.target) 
            self.logger.debug("filter path %s", self.filter)
            #Run rsync
            command = self._prepare_rsync_command()
            self._run_command(command)
            #Job done, update the time in the database
            self._set_lastbackup_time()
            #Remove old snapshots, local only
            if self.destination.is_dir() and self.snapshot:
                dest = os.path.join(self.destination.path, self.name)
                self._delete_old_files(dest, days=self.duration, keep=self.keep)
                #Symlink
                last = os.path.join(self.destination.path, self.name, 'last')
                if os.path.islink(last):
                    os.remove(last)
                os.chdir(os.path.dirname(self.current_backup_path))
                try:
                    os.symlink(os.path.basename(self.current_backup_path), last)
                except FileExistsError:
                    self.logger.warn('The symlink %s could not be created because a file exists', last)
                except AttributeError:
                    self.logger.warn('Attribute error for symlink. Job: %s', self.name) 


