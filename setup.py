#!/usr/bin/env python

#from distutils.core import setup
from setuptools import setup, find_packages
from Vitalus import __version__
from Vitalus import info

setup(
    name         = 'Vitalus',
    version      = __version__,
    url          = info.URL,
    author       = "Francois Boulogne",
    author_email = info.EMAIL,
    description  = info.SHORT_DESCRIPTION,
    packages     = find_packages(),
    scripts      = [],
    #test_suite   = "nose.collector",
)
