#!/usr/bin/env python

from distutils.core import setup
from Vitalus import info

setup(
    name         = 'Vitalus',
    version      = info.VERSION,
    url          = info.URL,
    author       = "François Boulogne",
    author_email = info.EMAIL,
    description  = info.SHORT_DESCRIPTION,
    packages = ['Vitalus'],
    scripts     = ['vitalus.py'],
)
