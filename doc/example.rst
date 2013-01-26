Example
=======

This is an example. To know more about the API, read the :doc:`vitalus` documentation.

.. code-block:: python

    #!/usr/bin/env python

    # This file is an example
    # It is designed to be run frequently
    # by a cron job (e.g. each few hours)

    import Vitalus.vitalus as vitalus

    # Create an instance
    # Default: log are in ~/.backup. You can change it with log_path=/foo
    my_backup = vitalus.Vitalus()


    # When I want to check my script, I set the log level to DEBUG.
    # This give you a chance to understand what's going wrong.
    # The default is INFO, so WARNING or CRITICAL messages are printed in logs
    # Logs are storred in ~/.backup. They are rotated once a day.
    my_backup.set_log_level('DEBUG')

    # This is my external disk
    my_backup.set_destination('/media/disk/backup')

    # I add a job for 'my_documents'
    # I want to keep increments (default: False)
    my_backup.add_job('my_documents', '/home/myself/documents', history=True)

    # Copy data excepting *.html files.
    # This is a rsync filter rule (man rsync to learn more)
    # filter is a tuple. Don't forget the coma.
    my_backup.add_job('my_data', '/home/myself/data', history=True, filter=('- *.html',))

    # Another job
    # minimal duration between two backups: 5 hours (default: 24h)
    my_backup.add_job('thunderbird', '/home/myself/.thunderbird', period=5, history=False)


    # Sync my home space on a server to my disk
    # Keys, without password must be configured
    my_backup.add_job('server', 'myself@server.tld:.')


    # Let's go!
    my_backup.run()

    # Read the log in ~/.backup
