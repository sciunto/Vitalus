#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest 
import tempfile

from job import Target


class TestTarget(unittest.TestCase):

    #
    # Simple domain
    #
    def test_is_ssh_ssh_domain(self):
        target = Target('fr@sciunto.org:.')
        self.assertTrue(target.is_ssh())

    def test_is_dir_ssh_domain(self):
        target = Target('fr@sciunto.org:.')
        self.assertFalse(target.is_dir())

    #
    # IPv4
    #
    def test_is_ssh_ssh_ipv4(self):
        target = Target('fr@192.168.1.30:.')
        self.assertTrue(target.is_ssh())

    def test_is_dir_ssh_ipv4(self):
        target = Target('fr@192.168.1.30:.')
        self.assertFalse(target.is_dir())

    #
    # Directory
    #
    def test_is_dir_dir_abs(self):
        tmp = tempfile.TemporaryDirectory(suffix='', prefix='tmp', dir=None)
        target = Target(tmp.name)
        self.assertTrue(target.is_dir())

    def test_is_ssh_dir_abs(self):
        tmp = tempfile.TemporaryDirectory(suffix='', prefix='tmp', dir=None)
        target = Target(tmp.name)
        self.assertFalse(target.is_ssh())

if __name__ == '__main__':
    unittest.main()

