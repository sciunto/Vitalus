#!/usr/bin/env python

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

import psutil, os, sys
import subprocess
import shutil
import datetime
import logging, logging.handlers
import tarfile
import re
import signal
import shelve


class TARGETError(Exception):
    """
    Class: exception for target validity
    """
    def __init__(self):
        Exception.__init__(self)


class Vitalus:
    """
    Class for backups
    """
    def __init__(self, min_disk_space=1):
        """
        min_disk_space: minimal disk space (destination) [Go]
        """
        #Variables
        self.now = datetime.datetime.now()
        self.current_date = self.now.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        self.jobs = []
        self.terminate = False
        self.min_disk_space = min_disk_space * 10**9

        #Logging
        self.backup_log_dir = os.path.expanduser('~/.backup/')
        if not os.path.isdir(self.backup_log_dir):
            os.makedirs(self.backup_log_dir)
        self.pidfilename = os.path.join(self.backup_log_dir, 'backup.pid')

        self.logger = logging.getLogger('Vitalus')
        LOG_PATH = os.path.join(self.backup_log_dir, 'backup.log')
        #hdlr = logging.FileHandler(os.path.join(self.backup_log_dir, 'backup.log'))

        # Add the log message handler to the logger
        log_rotator = logging.handlers.TimedRotatingFileHandler(LOG_PATH, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        log_rotator.setFormatter(formatter)
        self.logger.addHandler(log_rotator)
        
        self.logger.setLevel(logging.INFO)

        #Priority 
        self._set_process_low_priority()

        #timebase
        self._timebase = shelve.open(os.path.join(self.backup_log_dir, 'time.db'))
        signal.signal(signal.SIGTERM, self._signal_handler)
   
    def __del__(self):
        self._timebase.close()

    def set_log_level(self, level='INFO'):
        """
        Set the logger level (INFO, CRITICAL, DEBUG, ERROR, FATAL)
        """
        if level == 'INFO':
            self.logger.setLevel(logging.INFO)
            self.logger.info('Set logger level: ' + level)
        elif level == 'CRITICAL':
            self.logger.setLevel(logging.CRITICAL) 
            self.logger.info('Set logger level: ' + level)
        elif level == 'DEBUG':
            self.logger.setLevel(logging.DEBUG)   
            self.logger.info('Set logger level: ' + level)
        elif level == 'ERROR':
            self.logger.setLevel(logging.ERROR)   
            self.logger.info('Set logger level: ' + level)
        elif level == 'FATAL':
            self.logger.setLevel(logging.FATAL)
            self.logger.info('Set logger level: ' + level)
        else:
            self.logger.ERROR('Unknown level')
            
        

    def _set_lastbackup_time(self, name):
        """
        Set the last backup (labeled name) time 
        """
        self.logger.debug('Set lastbackup time')
        self._timebase[name] = datetime.datetime.now() 

    def _check_need_backup(self, name, period):
        """
        Return True if backup needed
        False otherwise
        name (backup label)
        period (seconds)
        """
        self.logger.debug('Check time between backups for ' + str(name))
        try:
            last = self._timebase[name]
        except KeyError:
            #Not yet stored
            #Run the first backup
            self.logger.debug(str(name) + ': first backup')
            return True
       
        #Calculate the difference
        self.logger.debug('now=' + str(datetime.datetime.now()) + ' seconds')
        self.logger.debug('last=' + str(last) + ' seconds')
        diff = datetime.datetime.now() - last
        difftime = diff.seconds + diff.days * 3600*24
        self.logger.debug('diff=' + str(difftime) + ' seconds')
        self.logger.debug('period=' + str(period) + ' seconds')
        if difftime > period:
            self.logger.debug(str(name) + ' need backup')
            return True
        else:
            self.logger.debug(str(name) + ' does not need backup')
            return False

    def _signal_handler(self, signal, frame):
        self.logger.warn('Signal received %s' % signal)
        self._set_process_high_priority()
        self.terminate = True

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

        pidfile = open(self.pidfilename, "w")
        pidfile.write("%s" % os.getpid())
        pidfile.close

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

    def _delete_old_files(self, path, days=10, keep=10):
        """ Delete files older than #days
        but keep at least #keep files
        """
        if self.terminate: return
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


    def _compress(self, path):
        """ Compress the directory """
        self.logger.debug('Zip the directory: ' + str(path))
        head, tail = os.path.split(path)
        archive = str(path) + '.bz2'
        tar = tarfile.open(archive, "w:bz2")
        tar.add(path, arcname=tail)
        tar.close()

    def _check_target(self, target):
        """ Check the target"""
        if re.match('[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]+\:.*', target):
            #ssh
            self.logger.debug('the target looks like SSH')
            #TODO check connection
            return 'SSH'
        else:
            if not os.path.exists(target):
                self.logger.warn('target %s: does not exist' % target)
                self.logger.info('Aborting...')
                raise TARGETError
            else:
                return 'DIR'

    def _do_backup(self, name, source, destination, incremental=False, duration=50, filter=None):
        """ Backup fonction
        make rsync command and run it
        """
        #TODO it might be worth to reduce the length of this method!

        #If a signal is received, stop the process
        if self.terminate: return

        self.logger.info('backup %s' % name)

        #Check if the source exists
        try:
            source_type = self._check_target(source)
        except TARGETError:
            return

        #check if the destination exists
        try:
            dest_type = self._check_target(destination)
        except TARGETError:
            return

        #TODO: run the command though ssh...
        if dest_type != 'SSH':
            if psutil.disk_usage(destination)[2] < self.min_disk_space:
                self.logger.critical('Low disk space: ' + str(destination))
                return

        #Logs
        job_log = os.path.join(self.backup_log_dir, name + '.log')
        job_logger = logging.getLogger(name)
        log_rotator = logging.handlers.TimedRotatingFileHandler(job_log, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        job_logger.addHandler(log_rotator)
        job_logger.setLevel(logging.INFO)
        job_logger.info('='*20 + str(self.now) + '='*20)


        #define dirs for the destination
        #create them if needed
        if dest_type != 'SSH':
            dest_dir_path = destination
            if incremental:
                inc_dir = os.path.join(destination, str(name), 'INC')
                inc_path = os.path.join(inc_dir, self.current_date)
                self.logger.debug('increment path: %s' % inc_path)

            backup = os.path.join(dest_dir_path, str(name), 'BAK')

            #Create dirs (locally)
            try:
                if incremental:
                    os.makedirs(inc_path)
                os.makedirs(backup)
            except OSError:
                #they could already exist
                pass
        else:
            # Create dirs on the server
            login, dest_dir_path = destination.split(':')

            if incremental:
                inc_dir = os.path.join(dest_dir_path, str(name), 'INC')
                inc_path = os.path.join(inc_dir, self.current_date)
                #add ~/ if does not start with /
                if not inc_path.startswith('/'):
                    inc_path = os.path.join('~', inc_path)
                self.logger.debug('increment path: %s' % inc_path)

                process = subprocess.Popen(['ssh', '-t', login, 'mkdir', '-p', inc_path], bufsize=4096, stdout=subprocess.PIPE)
                stdout, stderr = process.communicate()
                self.logger.debug('SSH mkdir INC: ' + stdout.decode())
                self.logger.warning('SSH mkdir INC: ' + stderr.decode())

            back_path = os.path.join(dest_dir_path, str(name), 'BAK')
            process = subprocess.Popen(['ssh', '-t', login, 'mkdir', '-p', back_path], bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            self.logger.debug('SSH mkdir BAK: ' + stdout.decode())
            self.logger.warning('SSH mkdir BAK: ' + stderr.decode())
            backup = login + ':' + back_path

        self.logger.debug('source path: %s' % source)
        self.logger.debug('backup path: %s' % backup)
        self.logger.debug('filter path: %s' % filter)


        #Compose the command
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
        if (source_type or dest_type) == 'SSH':
            command.append('-z')

        # backup-dir: keep increments
        if incremental:
            command.append('--backup')
            command.append('--backup-dir=' + inc_path)

        # Add source and destination
        command.append(source)
        command.append(backup)

        if filter:
            # Add filters, the resulting command must look like
            # rsync -av a b --filter='- *.txt' --filter='- *dir'
            for element in filter:
                command.append('--filter=' + element)
                self.logger.debug('add filter: ' + element)

        #If a signal is received, stop the process
        if self.terminate: return

        #Run the command
        self.logger.debug('rsync command: %s' % command)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        #Dump outputs in log files
        log = stdout.decode()
        job_logger.info(log)

        if stderr != b'':
            job_logger.info('Errors:')
            job_logger.info(stderr.decode())

        #Crompress Increments
        if incremental:
            if dest_type != 'SSH':
                #compress if not empty
                if os.listdir(inc_path) != []:
                    self._compress(inc_path)
                else:
                    self.logger.info('Empty increment')
                #delete the dir (we keep only non-empty tarballs
                shutil.rmtree(inc_path)

                #MrProper: remove old tarballs
                self._delete_old_files(inc_dir, days=duration)
            else:
                pass
                #TODO ! compress dir though ssh
                #TODO Remove old dirs though ssh

        #Job done, update the time in the database
        self._set_lastbackup_time(name)

    def add_job(self, name, source, destination, period=24, incremental=False, duration=50, filter=None):
        """ Add a new job 
        name: backup label
        source: backup from...
        destination: backup to...
        period: min time (hours) between backups
        incremental: Create diffs
        duration: How long we keep diffs (days)
        filter: filter, must be a tuple
        """
        period_in_seconds = period * 3600
        self.logger.debug('add job+ ' + 'name' + str(name))#+ 'source'+source+ 'destination'+destination+\
            #'period'+period_in_seconds+ 'incremental'+incremental+ 'duration'+duration+ 'filter'+filter)
        self.jobs.append({'name':name, 'source':source, 'destination':destination,\
            'period':period_in_seconds, 'incremental':incremental, 'duration':duration, 'filter':filter})

    def run(self):
        """ Run all jobs """
        self.logger.info('The script starts...')
        self._create_pidfile()
        for job in self.jobs:
            if self._check_need_backup(job['name'], job['period']): 
                print(job['name'])
                self._do_backup(job['name'], job['source'], job['destination'], job['incremental'], job['duration'], job['filter'])
        self._release_pidfile()
        self.logger.info('The script exited gracefully')

if __name__ == '__main__':
    #An example...
    b = Vitalus(min_disk_space=0.1)
    b.set_debug_level('DEBUG')
    b.add_job('test', '/home/gnu/tmp/firefox', '/tmp/sauvegarde', period=0.0, incremental=True)
    b.add_job('test2', '/home/gnu/tmp/debian', '/tmp/sauvegarde', incremental=True)
    b.add_job('test3', '/home/gnu/tmp/photos', '/tmp/sauvegarde', incremental=True)
    b.add_job('test4', '/home/gnu/tmp/www', '/tmp/sauvegarde', period=0, incremental=True)

    b.run()
