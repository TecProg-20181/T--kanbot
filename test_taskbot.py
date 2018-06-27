# -*- coding: utf-8 -*-

import unittest
from tasks_controller import TasksController

class TestTaskBot(unittest.TestCase):
    id = ''

    def test_anew_task(self):
        command = TasksController.new_task('TESTE', 12234)
        self.id = command[18]
        print(command)
        self.assertEqual(command, 'New task *TODO* [[{}]] TESTE'.format(self.id))

    def test_delete_task(self):
        self.test_anew_task()
        command = TasksController.delete_task(self.id, 12234)
        self.assertEqual(command, 'Task [[{}]] deleted'.format(self.id))


suite = unittest.TestLoader().loadTestsFromTestCase(TestTaskBot)
unittest.TextTestRunner(verbosity=2).run(suite)
