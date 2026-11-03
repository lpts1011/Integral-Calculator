import os
import time
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication
from qt_jobs import JobRunner


def delayed_value():
    time.sleep(.25)
    return 42


class JobRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def until(self, condition, timeout=10):
        started = time.monotonic()
        while not condition() and time.monotonic() - started < timeout:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(condition())

    def test_background_job_returns_without_blocking_and_delivers_on_ui_thread(self):
        runner = JobRunner()
        received, errors = [], []
        started = time.monotonic()
        runner.submit(delayed_value, (), lambda value: received.append((value, QThread.currentThread())), errors.append)
        self.assertLess(time.monotonic() - started, .1)
        self.until(lambda: not runner.busy)
        self.assertEqual(errors, [])
        self.assertEqual(received[0][0], 42)
        self.assertEqual(received[0][1], self.app.thread())
        runner.close()

    def test_closed_runner_suppresses_result_callbacks(self):
        runner = JobRunner()
        received, errors = [], []
        runner.submit(delayed_value, (), received.append, errors.append)
        runner.close()
        deadline = time.monotonic() + .5
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertEqual(received, [])
        self.assertEqual(errors, [])
