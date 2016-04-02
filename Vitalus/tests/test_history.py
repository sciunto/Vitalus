#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import datetime

from Vitalus.history import older


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
