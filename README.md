# Author 
F. Boulogne <fboulogne at april dot org>

# License 

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>

# Description
Wrapper for rsync


# Functionalities
* Manage different tasks
* rsync from or to local disks
* rsync from or to SSH
* Check disk space (local disks)
* Possibility to keep zipped increments
* Old increments deleted (keeping a minimal amount of increments)
* Rotated logs (general + one per task)

# Requirements
* python 3
* python-psutil
* rsync
* distutils (install)

# How to install?
Archlinux: https://aur.archlinux.org/packages.php?ID=61901

Otherwise:
python setup.py install --root='/tmp'
You can adapt the root directory.

# How to setup?
See example.py
