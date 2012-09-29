.. Vitalus documentation master file, created by
   sphinx-quickstart on Wed Sep 26 22:28:07 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Vitalus's documentation!
===================================

Contents:

.. toctree::
    :maxdepth: 2
    
    vitalus


Functionalities
==============
* Manage different tasks
* rsync from or to local disks
* rsync from or to SSH
* Check disk space (local disks)
* Possibility to keep zipped increments
* Old increments deleted (keeping a minimal amount of increments)
* Rotated logs (general + one per task)

How to install?
===============
Archlinux: https://aur.archlinux.org/packages.php?ID=61901

Otherwise:
python setup.py install --root='/tmp'
You can adapt the root directory.

Requirements
------------
* python 3
* python-psutil
* rsync
* distutils (install)

How to setup?
=============
See example.py


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

