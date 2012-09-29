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
import utils
import datetime
import logging

class Job:
    """
    Class containing a job

    :param min_disk_space: minimal disk space
    :param log_dir: Log directory path
    :param name: Job name
    :param source: Source path
    :param destination: Destination path
    :param incremental: Activate incremental backup (Boolean)
    :param duration: How many days incrementals are kept
    :param keep: How many incrementals are (at least) kept
    :param filter: Rsync filters
    """
    #TODO signal...

    def __init__(self, min_disk_space, log_dir, name, source, destination, period, incremental, duration, keep, filter):
       
        self.min_disk_space = min_disk_space
        self.name = name
        self.source = source
        self.destination = destination
        self.period = period
        self.incremental = incremental
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
            self.logger.debug('the target looks like SSH')
            return 'SSH'
        else:
            if not os.path.exists(target):
                self.logger.warn('target %s: does not exist' % target)
                self.logger.info('Aborting...')
                raise TARGETError('Target %s: does not exist' % target)
            else:
                return 'DIR'

    def _check_disk_usage(self):
        """
        Check the disk usage
        :raises TARGETError: if low disk space
        """
        if self.dest_type == 'DIR':
            if psutil.disk_usage(self.destination)[2] < self.min_disk_space:
                self.logger.critical('Low disk space: ' + str(self.destination))
                raise TARGETError('Low disk space on %s' % self.destination)
        elif self.dest_type == 'SSH':
            #TODO
            pass

    def _set_lastbackup_time(self):
        """
        Set the last backup (labeled name) time 
        """
        self.logger.debug('Set lastbackup time')
        timebase = shelve.open(os.path.join(self.backup_log_dir, 'time.db')) #FIXME with ?
        timebase[self.name] = datetime.datetime.now() 
        timebase.close()


    def _check_need_backup(self):
        """
        Return True if backup needed
        False otherwise

        :returns: bool
        """
        self.logger.debug('Check time between backups for ' + str(self.name))
        try:
            timebase = shelve.open(os.path.join(self.backup_log_dir, 'time.db')) #FIXME with ?
            last = timebase[self.name]
            timebase.close()
        except KeyError:
            #Not yet stored
            #Run the first backup
            self.logger.debug(str(self.name) + ': first backup')
            return True
       
        #Calculate the difference
        self.logger.debug('now=' + str(datetime.datetime.now()) + ' seconds')
        self.logger.debug('last=' + str(last) + ' seconds')
        diff = datetime.datetime.now() - last
        difftime = diff.seconds + diff.days * 3600*24
        self.logger.debug('diff=' + str(difftime) + ' seconds')
        self.logger.debug('period=' + str(self.period) + ' seconds')
        if difftime > self.period:
            self.logger.debug(str(self.name) + ' need backup')
            return True
        else:
            self.logger.debug(str(self.name) + ' does not need backup')
            return False

    def _delete_old_files(self, path, days=10, keep=10):
        """
        Delete old archives in a path

        :param path: path to clean
        :param days: delete files older than this value
        :param keep: keep at least this amount of archives
        """
        ####if self.terminate: return
        filenames = [os.path.join(path, el) for el in os.listdir(path) if os.path.isfile(os.path.join(path, el))]
        #delete first the older one
        filenames.sort()
        nb_archives = len(filenames)
        for filepath in enumerate(filenames):
            #keep a sufficient number of archives
            if (nb_archives - filepath[0]) <= keep:
                self.logger.debug('nb archives %s, keep %s, archive %s' % (nb_archives, keep, filepath[0]))
                return
            #Are they too old?
            file_date = datetime.datetime.fromtimestamp(os.path.getmtime(filepath[1]))
            if datetime.datetime.now() - file_date - datetime.timedelta(days=days) < datetime.timedelta():
                self.logger.info('remove %s' % filepath[1])
                try:
                    os.remove(filepath[1])
                except OSError:
                    self.logger.warn('Impossible to remove %s' % filepath[1])

            else:
                self.logger.debug('keep %s' % filepath[1])
                return





    def _prepare_destination(self): 
        """
        Prepare the destination to receive a backup:
        * create dirs
        * Initialize paths
        """
        #define dirs for the destination
        #create them if needed
        if self.dest_type != 'SSH':
            dest_dir_path = self.destination
            if self.incremental:
                inc_dir = os.path.join(self.destination, str(self.name), 'INC')
                inc_path = os.path.join(inc_dir, str(self.current_date))
                self.logger.debug('increment path: %s' % inc_path)

            backup = os.path.join(dest_dir_path, str(self.name), 'BAK')

            #Create dirs (locally)
            try:
                if self.incremental:
                    os.makedirs(inc_path)
                os.makedirs(backup)
            except OSError:
                #they could already exist
                pass
        else:
            # Create dirs on the server
            login, dest_dir_path = destination.split(':')

            if incremental:
                inc_dir = os.path.join(dest_dir_path, str(self.name), 'INC')
                inc_path = os.path.join(inc_dir, self.current_date)
                #add ~/ if does not start with /
                if not inc_path.startswith('/'):
                    inc_path = os.path.join('~', inc_path)
                self.logger.debug('increment path: %s' % inc_path)

                process = subprocess.Popen(['ssh', '-t', login, 'mkdir', '-p', inc_path], bufsize=4096, stdout=subprocess.PIPE)
                stdout, stderr = process.communicate()
                self.logger.debug('SSH mkdir INC: ' + stdout.decode())
                #self.logger.warning('SSH mkdir INC: ' + stderr.decode())

            back_path = os.path.join(dest_dir_path, str(name), 'BAK')
            process = subprocess.Popen(['ssh', '-t', login, 'mkdir', '-p', back_path], bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            self.logger.debug('SSH mkdir BAK: ' + stdout.decode())
            #self.logger.warning('SSH mkdir BAK: ' + stderr.decode())
            backup = login + ':' + back_path

        self.backup_path = backup
        self.inc_path = inc_path
        self.inc_dir = inc_dir



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
        # delete-filterd: if a file is deleted in source, delete it in backup
        command.append('-avh') 
        command.append('--stats')
        command.append('--delete-excluded')
        # z: compress the flux if transfert thought a network
        if (self.source_type or self.dest_type) == 'SSH':
            command.append('-z')

        # backup-dir: keep increments
        if self.incremental:
            command.append('--backup')
            command.append('--backup-dir=' + self.inc_path)

        # Add source and destination
        command.append(self.source)
        command.append(self.backup_path)

        if self.filter:
            # Add filters, the resulting command must look like
            # rsync -av a b --filter='- *.txt' --filter='- *dir'
            for element in self.filter:
                command.append('--filter=' + element)
                self.logger.debug('add filter: ' + element)
                
        self.logger.debug('rsync command: %s' % command)
        return command

    def _compress_increments(self):
        """
        Compress increments
        """
        if self.incremental:
            if self.dest_type == 'DIR':
                #compress if not empty
                if os.listdir(self.inc_path) != []:
                    self.logger.debug('Zip the directory: ' + str(path))
                    utils.compress(self.inc_path)
                else:
                    self.logger.info('Empty increment')
                    pass
                #delete the dir (we keep only non-empty tarballs
                shutil.rmtree(self.inc_path)

                #MrProper: remove old tarballs
                self._delete_old_files(self.inc_dir, days=self.duration, keep=self.keep)
            elif self.dest_type == 'SSH':
                pass
                #TODO ! compress dir though ssh
                #TODO Remove old dirs though ssh

    def _do_backup(self):
        """ Backup fonction
        """
        #TODO it might be worth to reduce the length of this method!
        #It must be short enough to go in run()

        #If a signal is received, stop the process
        #FIXME if self.terminate: return


        self._prepare_destination()

        self.logger.debug('source path: %s' % self.source)
        self.logger.debug('backup path: %s' % self.backup_path)
        self.logger.debug('filter path: %s' % self.filter)


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

        self._compress_increments() #FIXME: bug... remove non empty increments

        #Job done, update the time in the database
        self._set_lastbackup_time()


    def run(self):
        """Run...
        """
        if self._check_need_backup():
            print(self.name)
            self.logger.info('backup %s' % self.name)
            self._do_backup()