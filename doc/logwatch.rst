Logwatch
========

Goal
----

If you have very sensitive data, desktops, servers, I would advice to monitor
your machines. Logwatch is a simple set of script which reads your logs and
send you tidy and readable emails. The goal of this page is to setup logwatch
for Vitalus.

Setup
-----

* In services/vitalus.log

.. code-block:: conf

    # this is in the format of <name> = <value>.  Whitespace at the beginning
    # and end of the lines is removed.  Whitespace before and after the = sign
    # is removed.  Everything is case *insensitive*.

    # Yes = True  = On  = 1
    # No  = False = Off = 0

    Title = "Vitalus"

    # Which logfile group...
    LogFile = vitalus



* In logfiles/vitalus.conf (don't forget to adapt the paths)

.. code-block:: conf

    # What actual file?  Defaults to LogPath if not absolute path....
    #Solaris is /var/cron/log -mgt
    LogFile = /root/.backup/backup.log

    # If the archives are searched, here is one or more line
    # (optionally containing wildcards) that tell where they are...
    Archive = /root/.backup/backup.log.*

* In scripts/services/, put the script available in Vitalus sources in logwatch/scripts/services/.


