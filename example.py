#!/usr/bin/env python


# This file is an example
# It is designed to be run frequently
# by a cron job (e.g. each few hours)

import Vitalus.vitalus as vitalus

# Create an instance
# min_disk_space correspond to the minimal disk space (destination)
# if it is lower, the backup is aborted and a critical message written in log
my_backup = vitalus.Vitalus(min_disk_space=0.5)


# When I want to check my script, I set the log level to DEBUG.
# This give you a chance to understand what's going wrong.
# The default is INFO, so WARNING or CRITICAL messages are printed in logs
# Logs are storred in ~/.backup. They are rotated once a day.
my_backup.set_log_level('DEBUG')

# This is my external disk
my_backup.set_destination('/media/disk/backup')

# I add a job for 'my_documents'
# I want to keep increments (default: False)
my_backup.add_job('my_documents', '/home/myself/documents', incremental=True)

# Copy data excepting *.html files.
# This is a rsync filter rule (man rsync to learn more)
# filter is a tuple. Don't forget the coma.
my_backup.add_job('my_data', '/home/myself/data', incremental=True, filter=('- *.html',))

# Another job
# minimal duration between two backups: 5 hours (default: 24h)
my_backup.add_job('thunderbird', '/home/myself/.thunderbird', period=5, incremental=False)


# Sync my home space on a server though SSH
# Keys, without password must be configured
my_backup.add_job('server', 'myself@server.tld:.')


# Let's go!
my_backup.run()

# Read the log in ~/.backup
