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
import logging
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
    def __init__(self):
        #Variables
        self.now = datetime.datetime.now()
        self.current_date = self.now.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        self.jobs = []
        self.terminate = False

        #Logging
        self.backup_log_dir = os.path.expanduser('~/.backup/')
        if not os.path.isdir(self.backup_log_dir):
            os.makedirs(self.backup_log_dir)
        self.pidfilename = os.path.join(self.backup_log_dir, 'backup.pid')

        self.logger = logging.getLogger('Vitalus')
        hdlr = logging.FileHandler(os.path.join(self.backup_log_dir, 'backup.log'))
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)

        #Priority 
        self._set_process_low_priority()

        #timebase
        self._timebase = shelve.open(os.path.join(self.backup_log_dir, 'time.db'))
        signal.signal(signal.SIGTERM, self._signal_handler)
   
    def __del__(self):
        self._timebase.close()

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
        diff = datetime.datetime.now() - last
        self.logger.debug('diff=' + str(diff.seconds) + ' seconds')
        self.logger.debug('period=' + str(period) + ' seconds')
        if diff.seconds > period:
            self.logger.debug(str(name) + ' need backup')
            return True
        else:
            self.logger.debug(str(name) + ' does not need backup')
            return False

    def _signal_handler(self, signal, frame):
        self.logger.warn('Signal received %s' % signal)
        self._set_process_high()
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

    def _set_process_high(self):
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

    def _do_backup(self, name, source, destination, incremental=False, duration=50, exclude=None):
        """ Backup fonction
        make rsync command and run it
        """
        if self.terminate: return
        self.logger.info('backup %s' % name)
        thread_log = os.path.join(self.backup_log_dir, name + '.log')

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

        with open(thread_log, 'a') as f:
            f.write('\n\n' + '='*20 + str(self.now) + '='*20 + '\n\n')
            f.close()

        #define dirs
        if incremental:
            incrementdir = os.path.join(destination, str(name), 'INC')
            increment = os.path.join(incrementdir, self.current_date)
            self.logger.debug('increment path: %s' % increment)

        backup = os.path.join(destination, str(name), 'BAK')
        self.logger.debug('source path: %s' % source)
        self.logger.debug('backup path: %s' % backup)
        self.logger.debug('exclude path: %s' % exclude)

        #Create dirs
        try:
            if incremental:
                os.makedirs(increment)
            os.makedirs(backup)
        except OSError:
            #they could already exist
            pass

        command = '/usr/bin/rsync'
        # a: archive (recursivity, preserve rights and times...)
        # v: verbose
        # h: human readable
        # stat: file rate stats
        # delete-excluded: if a file is deleted in source, delete it in backup
        command += ' -avh --stats --delete-excluded '
        # z: compress if transfert thought a network
        if (source_type or dest_type) == 'SSH':
            command += ' -z '

        # backup-dir: keep increments
        if incremental:
            command += ' --backup --backup-dir=%s %s %s' % (increment, source, backup)
        else:
            command += ' %s %s' % (source, backup)
        if exclude:
            #TODO check how it is formatted
            command += ' --exclude=' + exclude

        if self.terminate: return
        self.logger.debug('rsync command: %s' % command)

        #Run the command
        #FIXME : write command in a splitted version
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        #Write outputs
        loghandler = open(thread_log, 'a')
        loghandler.write(stdout.decode())
        if stderr != b'':
            loghandler.write('Errors:')
            loghandler.write(stderr.decode())
            

        if incremental:
            #compress & delete the dir
            self._compress(increment)
            shutil.rmtree(increment)

            #MrProper
            self._delete_old_files(incrementdir, days=duration)

        #Job done, update the time
        self._set_lastbackup_time(name)

    def add_job(self, name, source, destination, period=24, incremental=False, duration=50, exclude=None):
        """ Add a new job 
        name: backup label
        source: backup from...
        destination: backup to...
        period: min time (hours) between backups
        incremental: Create diffs
        duration: How long we keep diffs (days)
        exclude: Exclude a subpath #TODO
        """
        period_in_seconds = period*3600
        self.jobs.append({'name':name, 'source':source, 'destination':destination,\
            'period':period_in_seconds, 'incremental':incremental, 'duration':duration, 'exclude':exclude})

    def run(self):
        """ Run all jobs """
        self.logger.info('The script starts...')
        self._create_pidfile()
        for job in self.jobs:
            if self._check_need_backup(job['name'], job['period']): 
                print(job['name'])
                self._do_backup(job['name'], job['source'], job['destination'], job['incremental'], job['duration'], job['exclude'])
        self._release_pidfile()
        self.logger.info('The script exited gracefully')

if __name__ == '__main__':
    #An example...
    b = Vitalus()
    b.add_job('test', '/home/gnu/tmp/firefox', '/tmp/sauvegarde', period=0.01, incremental=True)
    b.add_job('test2', '/home/gnu/tmp/debian', '/tmp/sauvegarde', incremental=True)
    b.add_job('test3', '/home/gnu/tmp/photos', '/tmp/sauvegarde', incremental=True)
    b.add_job('test4', '/home/gnu/tmp/www', '/tmp/sauvegarde', period=0, incremental=True)

    b.run()
