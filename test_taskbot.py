# -*- coding: utf-8 -*-

import unittest
from taskbot import *

class TestTaskBot(unittest.TestCase):
    id = '4'

    def test_anew_task(self):
        command = TasksController.new_task('TESTE', '12234')
        self.id = command[18]
        print(command)
        self.assertEqual(command, 'New task *TODO* [[{}]] TESTE'.format(self.id))

    def test_delete_task(self):
        command = TasksController.delete_task(self.id, '12234')
        self.assertEqual(command, 'Task [[{}]] deleted'.format(self.id))


suite = unittest.TestLoader().loadTestsFromTestCase(TestTaskBot)
unittest.TextTestRunner(verbosity=2).run(suite)
