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
#import psutil
import subprocess
import shutil
import datetime
import logging

import Vitalus.utils as utils
from Vitalus.job import Target
from Vitalus.job import TARGETError
from Vitalus.job import Job


class RsyncJob(Job):
    """
    Class containing a rsync job

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
    :param snapshot: Activate (True) or desactivate (False) snapshots or simple (None) copy
    :type snapshot: bool or None
    :param duration: How many days snapshots are kept
    :type duration: int
    :param keep: How many snapshots are (at least) kept
    :type keep: int
    :param force: overide the timebase check, no min. duration.
    :type force: bool
    :param guid: (uid, gid) for destination
    :type guid: tuple
    :param filter: Rsync filters
    :type filter: list


    .. note::

        Source and destination path can be either real path
        or a ssh login joined to the path by a : character.

        if uid or gid are None, files owner are not changed
    """

    def __init__(self, log_dir, destination, name, source, period, snapshot, duration, keep, force, guid, filter):

        self.name = name
        self.source = Target(source)
        self.destination = Target(destination)
        self.period = period
        self.snapshot = snapshot
        self.duration = duration
        self.keep = keep
        self.filter = filter

        self.force = force
        self.now = datetime.datetime.now()
        self.current_date = self.now.strftime("%Y-%m-%d_%Hh%Mm%Ss")

        self.dest_uid, self.dest_gid = guid

        self.backup_log_dir = log_dir

        self.logger = logging.getLogger('Vitalus.RsyncJob')

        # Logs specific to the rsync job
        job_log = os.path.join(self.backup_log_dir, self.name + '.log')
        self.job_logger = logging.getLogger(self.name)
        log_rotator = logging.handlers.TimedRotatingFileHandler(job_log,
                                                                when='midnight',
                                                                interval=1,
                                                                backupCount=30,
                                                                encoding=None,
                                                                delay=False,
                                                                utc=False)
        self.job_logger.addHandler(log_rotator)
        self.job_logger.setLevel(logging.INFO)

        # Set previous and current backup paths
        self.previous_backup_path = None  # will be detected later
        self.current_backup_path = None

#    def _check_disk_usage(self):
#        """
#        Check the disk usage
#        :raises TARGETError: if low disk space
#        """
#        if self.destination.is_local():
#            #TODO, change the criterion
#            pass
#            #if psutil.disk_usage(self.destination)[2] < utils.get_folder_size(self.source):
#            #    self.logger.critical("Low disk space: %s", self.destination)
#            #    raise TARGETError('Low disk space on %s' % self.destination)
#        elif self.destination.is_ssh():
#            #TODO
#            pass

    def _delete_old_files(self, days=10, keep=10):
        """
        Delete old archives in the destination

        :param days: delete files older than this value
        :type days: int
        :param keep: keep at least this amount of archives
        :type keep: int
        """
        #TODO : review logs

        path = os.path.join(self.destination.path, self.name)

        self.destination.check_availability()
        if self.destination.is_local():
            filenames = os.listdir(path)
        elif self.destination.is_ssh():
                command = ['ssh', '-t', self.destination.login, 'ls', '-1', path]
                self.logger.debug('SSH ls command: ' + str(command))
                process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
                stdout, stderr = process.communicate()
                filenames = stdout.decode()
                filenames = filenames.split('\n')
                filenames = [x.strip('\r') for x in filenames if x != '']
        else:
            return

        to_delete = utils.get_older_files(filenames, days, keep)
        self.logger.debug("Backups available %s ", filenames)
        self.logger.debug("Backups to delete %s ", to_delete)

        self.destination.check_availability()
        if self.destination.is_local():
            for element in to_delete:
                self.logger.debug("Remove backup %s", element)
                try:
                    shutil.rmtree(os.path.join(path, element))
                except OSError:
                    self.logger.debug("Could not delete %s, try to chmod 644", os.path.join(path, element))
                    utils.r_chmod(os.path.join(path, element), 0o664)
                    try:
                        # try again
                        shutil.rmtree(os.path.join(path, element))
                    except OSError:
                        self.logger.error("Impossible to delete %s (symlink?)", os.path.join(path, element))
        elif self.destination.is_ssh():
            filepaths = [os.path.join(path, element) for element in to_delete]
            if filepaths != []:
                command = ['ssh', '-t', self.destination.login, 'rm', '-rf']
                command.extend(filepaths)
                self.logger.debug('SSH rm command: ' + str(command))
                process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
                stdout, stderr = process.communicate()

    def _get_last_backup(self):
        """
        Get the last backup path
        Return None if not available

        :returns: string
        """
        path = os.path.join(self.destination.path, self.name)
        self.destination.check_availability()
        if self.destination.is_local():
            if not os.path.isdir(path):
                return None
            #filenames = [os.path.join(path, el) for el in os.listdir(path)]
            filenames = os.listdir(path)
        elif self.destination.is_ssh():
            #First, create at least the target if does not exists
            command = ['ssh', '-t', self.destination.login, 'mkdir', '-p', path]
            self.logger.debug('SSH mkdir command: ' + str(command))
            process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            self.logger.debug('SSH mkdir result: ' + stdout.decode())

            command = ['ssh', '-t', self.destination.login, 'ls', '-1', path]
            self.logger.debug('SSH ls command: ' + str(command))
            process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            filenames = stdout.decode()
            filenames = filenames.split('\n')
            filenames = [x.strip('\r') for x in filenames if x != '']

        last = utils.get_last_file(filenames)
        if last is not None:
            last = os.path.join(path, last)
        self.logger.debug('_get_last_backup returns: %s', last)
        return last

    def _prepare_destination(self):
        """
        Prepare the destination to receive a backup:
        Create dirs
        """
        self.destination.check_availability()

        # Define current backup path
        if self.snapshot is True:
            self.current_backup_path = os.path.join(self.destination.path, self.name, str(self.current_date))
        elif self.snapshot is False:
            self.current_backup_path = os.path.join(self.destination.path, self.name, str(self.current_date))
        elif self.snapshot is None:
            self.current_backup_path = os.path.join(self.destination.path, self.name)
        else:
            raise ValueError('Wrong snapshot value (True, False or None)')

        # Make dirs
        if self.destination.is_local():
            if self.snapshot is True:
                os.makedirs(self.current_backup_path)  # This one does not exist!
            elif self.snapshot is False:
                if self.previous_backup_path is None:
                    os.makedirs(self.current_backup_path, exist_ok=True)
                else:
                    #Move dir to set the new date in the path
                    os.rename(self.previous_backup_path, self.current_backup_path)
            elif self.snapshot is None:
                os.makedirs(self.current_backup_path, exist_ok=True)
        elif self.destination.is_ssh():
            #Create dirs
            command = ['ssh', '-t', self.destination.login, 'mkdir', '-p', self.current_backup_path]
            self.logger.debug('SSH mkdir command: ' + str(command))
            process = subprocess.Popen(command, bufsize=4096, stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            self.logger.debug('SSH mkdir result: ' + stdout.decode())

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
        # L: turn symlinks to dir/file
        command.append('-avh')
        command.append('--stats')
        command.append('--delete')
        command.append('--delete-excluded')
        command.append('-L')

        # z: compress the flux if transfert thought a network
        if (self.source.is_ssh() or self.destination.is_ssh()):
            command.append('-z')
        if self.snapshot and self.previous_backup_path is not None:
            #Even if it works for ttype==Dir
            #It fails for ttype=SSH
            #If link-dest is not a relative path
            path = os.path.basename(self.previous_backup_path)
            command.append('--link-dest=../' + path)

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

        :param command: Command: each element is a part of the command line
        :type command: list

        .. note::

            Example of the command format
            command = ['/usr/bin/cp', '-r', '/home', '/tmp']
        """
        #Run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        #Dump outputs in log files
        log = stdout.decode()
        self.job_logger.info(log)

        if stderr != b'':
            self.job_logger.info('Errors:')
            self.job_logger.info(stderr.decode())

    def run(self, uid=None, gid=None):
        """
        Run the job.
        """
        self.logger.debug('Start rsync job: %s', self.name)
        #TODO rewriting and integration:
        #self._check_disk_usage()

        try:
            last_date = self._get_last_backup()
            if last_date is None:
                #It means that this is the first backup.
                self.previous_backup_path = None
            else:
                #self.previous_backup_path = os.path.join(self.destination.path, self.name, str(last_date))
                self.previous_backup_path = last_date

            self.logger.debug("Previous backup path: %s", self.previous_backup_path)
            self.logger.debug("Current backup path: %s", self.current_backup_path)

            if self._check_need_backup() or self.force:
                self.job_logger.info('='*20 + str(self.now) + '='*20)
                self.logger.debug('Start Backup: %s', self.name)
                print(self.name)

                # Prepare the destination
                self._prepare_destination()
                self.logger.debug("source path %s", self.source.target)
                self.logger.debug("destination path %s", self.destination.target)
                self.logger.debug("filter path %s", self.filter)

                # Run rsync
                command = self._prepare_rsync_command()
                self._run_command(command)

                # Job done, update the time in the database
                self._set_lastbackup_time()

                # Remove old snapshots
                self._delete_old_files(days=self.duration, keep=self.keep)

                # Create symlink
                if self.snapshot is True or self.snapshot is False:
                    last = os.path.join(self.destination.path, self.name, 'last')
                    if self.destination.is_local():
                        if os.path.islink(last):
                            os.remove(last)
                        os.chdir(os.path.dirname(self.current_backup_path))
                        try:
                            os.symlink(os.path.basename(self.current_backup_path), last)
                        except FileExistsError:
                            self.logger.warning('The symlink %s could not be created because a file exists', last)
                        except AttributeError:
                            self.logger.warning('Attribute error for symlink. Job: %s', self.name)
                    elif self.destination.is_ssh():
                        self.logger.warning('symlink for SSH not yet implemented')
                        #TODO Create symlink

                # UID/GID
                if self.dest_uid and self.dest_gid:
                    self._chown_destination(self.dest_uid, self.dest_gid)
                elif (self.dest_uid and not self.dest_gid) or (not self.dest_uid and self.dest_gid):
                    self.logger.error('uid or gid missing')

                self.logger.info("Backup %s done", self.name)
        except TARGETError as e:
            self.logger.warning(e)

    def _chown_destination(self, uid, gid):
        """
        Change owner of files in destination

        :param uid: user ID
        :param gid: group ID
        """
        if self.destination.is_local():
            self.logger.debug('chown %s %s for %s' % (uid, gid, self.current_backup_path))
            utils.r_chown(self.current_backup_path, uid, gid)
        elif self.destination.is_ssh():
            self.logger.warning('chown for SSH not yet implemented')
