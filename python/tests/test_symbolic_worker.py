import os
import threading
import time
import unittest
from unittest.mock import patch

import symbolic_service
from symbolic_service import run_isolated, warm_up


def identify_worker():
    return os.getpid()


def large_result():
    return 'payload' * 200000


def slow_result():
    time.sleep(2)
    return 'finished'


class SymbolicWorkerTests(unittest.TestCase):
    def test_resident_worker_reuses_process(self):
        self.assertEqual(run_isolated(identify_worker, ()), run_isolated(identify_worker, ()))

    def test_large_result_does_not_deadlock_waiting_for_exit(self):
        self.assertEqual(len(run_isolated(large_result, (), timeout=3)), 1400000)

    def test_timeout_replaces_worker(self):
        previous = run_isolated(identify_worker, ())
        with self.assertRaises(TimeoutError):
            run_isolated(slow_result, (), timeout=.1)
        self.assertNotEqual(previous, run_isolated(identify_worker, ()))

    def test_cancellation_interrupts_and_recovers(self):
        cancellation = threading.Event()
        timer = threading.Timer(.1, cancellation.set)
        timer.start()
        try:
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                run_isolated(slow_result, (), cancel=cancellation)
        finally:
            timer.cancel()
        self.assertIsInstance(run_isolated(identify_worker, ()), int)

    def test_warm_up_starts_reusable_worker(self):
        warm_up()
        self.assertIsInstance(run_isolated(identify_worker, ()), int)

    def test_failed_start_reports_original_error(self):
        symbolic_service._stop()
        with patch("multiprocessing.context.SpawnProcess.start", side_effect=OSError("cannot spawn")):
            with self.assertRaisesRegex(OSError, "cannot spawn"):
                run_isolated(identify_worker, ())
        self.assertIsInstance(run_isolated(identify_worker, ()), int)
