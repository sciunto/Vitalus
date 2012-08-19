#!/usr/bin/env python


# This file is an example
# It is designed to be run frequently
# by a cron job (e.g. each few hours)

import Vitalus.vitalus as vitalus

# Create an instance
# min_disk_space correspond to the minimal disk space (destination)
# if it is lower, the backup is aborted and a critical message written in log
my_backup = vitalus.Vitalus(min_disk_space=0.5)

# This is my external disk
target = '/media/disk/backup'

# I add a job for 'my_documents'
# I want to keep increments (default: False)
my_backup.add_job('my_documents', '/home/myself/documents', target, incremental=True)

# Another job
# minimal duration between two backups: 5 hours (default: 24h)
my_backup.add_job('thunderbird', '/home/myself/.thunderbird', target, period=5, incremental=False)


# Sync my home space on a server though SSH
# Keys, without password must be configured
my_backup.add_job('server', 'myself@server.tld:.', '/home/myself/backup_server')


# Let's go!
my_backup.run()

# Read the log in ~/.backup
