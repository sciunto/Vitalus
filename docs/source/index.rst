.. Vitalus documentation master file, created by
   sphinx-quickstart on Wed Sep 26 22:28:07 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Vitalus' documentation!
===================================

:Author: François Boulogne
:Download: `Stable version <http://source.sciunto.org/vitalus/>`_
:Developer's corner: `github.com project <https://github.com/sciunto/Vitalus>`_
:Generated: |today|
:License: GPL v3
:Version: |release|


Vitalus is a rsync wrapper. Rsync is a good atomic tool, but it needs to be wrapped to have a real backup solution.
Backup solutions are generally too basic or very difficult. This one fits my needs.

Contents:

.. toctree::
    :maxdepth: 2

    install
    example
    vitalus
    logwatch
    api

Philosophy
==========
* I want to centralize my backup in a unique script to achieve many tasks.
* I want to backup my desktop on external disks.
* I want to backup external disks to other external disks.
* I want to backup my /home/user on hosts accessible via ssh to a local disk.
* I want to backup my destop to hosts accessible via ssh.
* I want to keep increment if I need it.
* I want to adjust the frequency of copies for each task. The script starts much more frequently.
* I want readable log files telling me if everything goes fine.
* ...

Functionalities
===============
This is just another way to express the philosophy :)

* Manage different tasks
* rsync from and to local disks
* rsync from SSH to local disk
* rsync from local to SSH almost supported
* Check disk space (local disks)
* Keep track of time evolution (increments done with hard links), not possible via SSH for the moment.
* Old increments deleted (keeping a minimal amount of increments)
* Rotated logs (general + one per task)

How to install?
===============

See :doc:`install`.


How to setup?
=============
See :doc:`example`.

In my use case, I have a cron job running every hour. IMHO, this is quite atomic. Then, the script decides which task has to be done.

About ssh
---------
Keys must be configured with an empty passphrase.
Add in your ~/.ssh/config, something like

    Host sciunto.org
        IdentityFile ~/.ssh/key-empty-passphrase

Source or destination must have the format: login@server:path


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

