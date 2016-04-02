#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import datetime

from Vitalus.history import older
from Vitalus.history import older_keepmin


class TestOlder(unittest.TestCase):

    def test_wrong_day_value(self):
        with self.assertRaises(ValueError):
            older([], days=-3)

    def test_getOlderFiles_plenty_older(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1, 20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            # only these files are "old"
            if day >= 10:
                expected_list.append(filename)
        expected_list.sort()
        result = older(file_list, days=10)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_allnew(self):
        file_list = []
        now = datetime.datetime.now()
        for day in range(1, 9):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
        result = older(file_list, days=10)
        # Nothing must be deleted
        self.assertEqual(result, [])

class TestOlderKeep(unittest.TestCase):

    def test_wrong_keep_value(self):
        with self.assertRaises(ValueError):
            older_keepmin([], days=3, keep=-1)

    def test_wrong_day_value(self):
        with self.assertRaises(ValueError):
            older_keepmin([], days=-1, keep=0)

    def test_getOlderFiles_plenty_older_keep0(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1, 20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            if day >= 10:
                expected_list.append(filename)
        expected_list.sort()
        result = older_keepmin(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_plenty_older_keep0_unexpected(self):
        file_list = ['foo']
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1, 20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            if day >= 10:
                expected_list.append(filename)
        expected_list.sort()
        result = older_keepmin(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_no_older_keep0(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1, 9):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
        result = older_keepmin(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_zero_older_keep10(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1, 20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            expected_list.append(filename)

        expected_list = expected_list[10:]
        expected_list.sort()
        result = older_keepmin(file_list, days=0, keep=10)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_zero_file(self):
        # In this case, the number of file < keep
        file_list = []
        expected_list = []
        now = datetime.datetime.now()

        result = older_keepmin(file_list, days=0, keep=10)
        self.assertEqual(result, expected_list)
