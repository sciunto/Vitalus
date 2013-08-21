#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import tempfile

from Vitalus.job import Target
from Vitalus.job import TARGETError


class TestTarget(unittest.TestCase):

    #
    # Simple domain
    #
    def test_is_ssh_ssh_domain(self):
        target = Target('fr@sciunto.org:.')
        self.assertTrue(target.is_ssh())

    def test_is_dir_ssh_domain(self):
        target = Target('fr@sciunto.org:.')
        self.assertFalse(target.is_local())

    #
    # Complicated domain
    #
    def test_is_ssh_ssh_cdomain(self):
        target = Target('fr67-94@sub-extra.sciunto.org:.')
        self.assertTrue(target.is_ssh())

    #
    # IPv4
    #
    def test_is_ssh_ssh_ipv4(self):
        target = Target('fr@192.168.1.30:.')
        self.assertTrue(target.is_ssh())

    def test_is_dir_ssh_ipv4(self):
        target = Target('fr@192.168.1.30:.')
        self.assertFalse(target.is_local())

    #
    # Directory
    #
    def test_is_dir_dir_abs(self):
        tmp = tempfile.TemporaryDirectory(suffix='', prefix='tmp', dir=None)
        target = Target(tmp.name)
        self.assertTrue(target.is_local())

    def test_is_ssh_dir_abs(self):
        tmp = tempfile.TemporaryDirectory(suffix='', prefix='tmp', dir=None)
        target = Target(tmp.name)
        self.assertFalse(target.is_ssh())

    #
    # Wrong domain
    #
    def test_incompletedomain(self):
        target = Target('fr67-94@sub-extra.sciunto.org')
        self.assertRaises(TARGETError, lambda: target.check_availability())


if __name__ == '__main__':
    unittest.main()
