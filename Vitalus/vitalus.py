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


class Job:
    """
    Class containing a job
    """
    def __init__(self, logger, name, source, destination, period=24, incremental=False, duration=50, keep=10, filter=None):
        """
        logger:
        name:
        source:
        destination:
        incremental: Activate incremental backup (Boolean)
        duration: How many days incrementals are kept
        keep: How many incrementals are (at least) kept
        filter: 
        """
        
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

        self.backup_log_dir = '/tmp' #FIXME
        
        self.logger = logger #FIXME : define sub logger
        
        #Logs specific to the rsync job
        job_log = os.path.join(self.backup_log_dir, self.name + '.log')
        self.job_logger = logging.getLogger(self.name)
        log_rotator = logging.handlers.TimedRotatingFileHandler(job_log, when='midnight', interval=1, backupCount=30, encoding=None, delay=False, utc=False)
        self.job_logger.addHandler(log_rotator)
        self.job_logger.setLevel(logging.INFO)
        self.job_logger.info('='*20 + str(self.now) + '='*20)
        
            

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
        name (backup label)
        period (seconds)
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

    def _get_target_type(self, target):
        """
        Return the target type
        SSH if matches name@domaine.tld:dir
        DIR if it's a directory
        
        Raise
        -----
        TARGETError: weird target type 
        """
        if re.match('[a-zA-Z0-9+_\-\.]+@[0-9a-zA-Z][.-0-9a-zA-Z]*.[a-zA-Z]+\:.*', target):
            #ssh
            self.logger.debug('the target looks like SSH')
            return 'SSH'
        else:
            if not os.path.exists(target):
                self.logger.warn('target %s: does not exist' % target)
                self.logger.info('Aborting...')
                raise TARGETError
            else:
                return 'DIR'

    def _delete_old_files(self, path, days=10, keep=10):
        """
        Delete old archives in a path
        path: path to clean
        days: delete files older than this value
        keep: keep at least this amount of archives
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


    def _compress(self, path):
        """ Compress the directory """
        self.logger.debug('Zip the directory: ' + str(path))
        head, tail = os.path.split(path)
        archive = str(path) + '.bz2'
        tar = tarfile.open(archive, "w:bz2")
        tar.add(path, arcname=tail)
        tar.close()



    def _prepare_destination(self, dest_type): #FIXME dest_type (self ?)
        """
        Prepare the destination to receive a backup:
        * create dirs
        * Initialize paths
        """
        #define dirs for the destination
        #create them if needed
        if dest_type != 'SSH':
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



    def _prepare_rsync_command(self, source_type, dest_type): #FIXME (self ?)
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
        if (source_type or dest_type) == 'SSH':
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

    def _do_backup(self):
        """ Backup fonction
        """
        #TODO it might be worth to reduce the length of this method!
        #It must be short enough to go in run()

        #If a signal is received, stop the process
        #FIXME if self.terminate: return

        #Check if the source exists
        try:
            source_type = self._get_target_type(self.source)
        except TARGETError:
            return

        #check if the destination exists
        try:
            dest_type = self._get_target_type(self.destination)
        except TARGETError:
            return


        self._prepare_destination(dest_type)

        self.logger.debug('source path: %s' % self.source)
        self.logger.debug('backup path: %s' % self.backup_path)
        self.logger.debug('filter path: %s' % self.filter)


        command = self._prepare_rsync_command(source_type, dest_type)

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

        #Crompress Increments
        if self.incremental:
            if dest_type != 'SSH':
                #compress if not empty
                if os.listdir(self.inc_path) != []:
                    self._compress(self.inc_path)
                else:
                    self.logger.info('Empty increment')
                    pass
                #delete the dir (we keep only non-empty tarballs
                shutil.rmtree(self.inc_path)

                #MrProper: remove old tarballs
                self._delete_old_files(self.inc_dir, days=self.duration, keep=self.keep)
            else:
                pass
                #TODO ! compress dir though ssh
                #TODO Remove old dirs though ssh

        #Job done, update the time in the database
        self._set_lastbackup_time()


    def run(self):
        """Run...
        """
        if self._check_need_backup():
            print(self.name)
            self.logger.info('backup %s' % self.name)
            self._do_backup()

class Vitalus:
    """
    Class for backups
    """
    def __init__(self, min_disk_space=1):
        """
        min_disk_space: minimal disk space (destination) [Go]
        """
        #Variables

        self.jobs = []
        self.terminate = False
        self.min_disk_space = min_disk_space * 10**9

        self.destination = None

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
        
        signal.signal(signal.SIGTERM, self._signal_handler)

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

    def add_destination(self, destination):
        
        #TODO check if destination is valid
        #Otherwise, self.destination = None
        if True:
            self.destination = destination
        else:
            self.destination = None
            self.logger.warning('Wrong or unreachable destination')

    def add_job(self, name, source, period=24, incremental=False, duration=50, keep=10, filter=None):
        """ Add a new job 
        name: backup label
        source: backup from...
        destination: backup to...
        period: min time (hours) between backups
        incremental: Activate incremental backup (Boolean)
        duration: How many days incrementals are kept
        keep: How many incrementals are (at least) kept
        filter: filter, must be a tuple
        """
        if self.destination:
            period_in_seconds = period * 3600
            self.logger.debug('add job+ ' + 'name' + str(name))
            #self.jobs.append({'name':name, 'source':source, 'destination':destination,\
            #    'period':period_in_seconds, 'incremental':incremental, 'duration':duration, 'keep':keep, 'filter':filter})
            self.jobs.append(Job(self.logger, name, source, self.destination, period, incremental, duration, keep, filter))


    def run(self):
        """ Run all jobs """
        self.logger.info('The script starts...')
        self._create_pidfile()
        for job in self.jobs:
            job.run()
            #if self._check_need_backup(job['name'], job['period']): 
                #print(job['name'])
                #self._do_backup(job['name'], job['source'], job['destination'], 
                #incremental=job['incremental'], duration=job['duration'], keep=job['keep'], filter=job['filter'])
        self._release_pidfile()
        self.logger.info('The script exited gracefully')

if __name__ == '__main__':
    #An example...
    b = Vitalus(min_disk_space=0.1)
    b.set_log_level('DEBUG')
    b.add_destination('/tmp/sauvegarde')
    b.add_job('test', '/home/gnu/tmp/firefox', period=0.0, incremental=True)
    b.add_job('test2', '/home/gnu/tmp/debian', period=0.0, incremental=True)
    b.add_job('test3', '/home/gnu/tmp/photos', incremental=True)
    b.add_job('test4', '/home/gnu/tmp/www', period=0, incremental=True)

    b.run()
    
    
    
#TODOCheck disk usage
        ##TODO: run the command though ssh...
        #if dest_type != 'SSH':
            #if psutil.disk_usage(self.destination)[2] < self.min_disk_space:
                #self.logger.critical('Low disk space: ' + str(destination))
                #return
