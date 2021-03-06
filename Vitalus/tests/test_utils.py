#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Author: Francois Boulogne

from Vitalus.utils import get_older_files
from Vitalus.utils import get_last_file

import unittest
import datetime

class TestRecentFile(unittest.TestCase):

    def test_list_empty(self):
        file_list = []
        expected = None
        result = get_last_file(file_list)
        self.assertEqual(result, expected)

    def test_list_poison(self):
        file_list = ['poison']
        expected = None
        result = get_last_file(file_list)
        self.assertEqual(result, expected)


    def test_list_date(self):
        file_list = []
        now = datetime.datetime.now()
        for day in range(0,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)

        expected = now.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        result = get_last_file(file_list)
        self.assertEqual(result, expected)

    def test_list_date_reversed(self):
        file_list = []
        now = datetime.datetime.now()
        for day in range(0,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)

        file_list.reverse()
        expected = now.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        result = get_last_file(file_list)
        self.assertEqual(result, expected)

    def test_list_date_plus_poison(self):
        file_list = []
        now = datetime.datetime.now()
        for day in range(0,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)

        file_list.append('poison')

        expected = now.strftime("%Y-%m-%d_%Hh%Mm%Ss")
        result = get_last_file(file_list)
        self.assertEqual(result, expected)

class TestOlderFiles(unittest.TestCase):

    def test_wrong_keep_value(self):
        with self.assertRaises(ValueError):
            get_older_files([], days=3, keep=-1)

    def test_wrong_day_value(self):
        with self.assertRaises(ValueError):
            get_older_files([], days=-1, keep=0)

    def test_getOlderFiles_plenty_older_keep0(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            if day >= 10:
                expected_list.append(filename)
        expected_list.sort()
        result = get_older_files(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_plenty_older_keep0_unexpected(self):
        file_list = ['foo']
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            if day >= 10:
                expected_list.append(filename)
        expected_list.sort()
        result = get_older_files(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_no_older_keep0(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1,9):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
        result = get_older_files(file_list, days=10, keep=0)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_zero_older_keep10(self):
        file_list = []
        expected_list = []
        now = datetime.datetime.now()
        for day in range(1,20):
            date = now - datetime.timedelta(days=day)
            filename = date.strftime("%Y-%m-%d_%Hh%Mm%Ss")
            file_list.append(filename)
            expected_list.append(filename)

        expected_list = expected_list[10:]
        expected_list.sort()
        result = get_older_files(file_list, days=0, keep=10)
        self.assertEqual(result, expected_list)

    def test_getOlderFiles_zero_file(self):
        #In this case, the number of file < keep
        file_list = []
        expected_list = []
        now = datetime.datetime.now()

        result = get_older_files(file_list, days=0, keep=10)
        self.assertEqual(result, expected_list)
