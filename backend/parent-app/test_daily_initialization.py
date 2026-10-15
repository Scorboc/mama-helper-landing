"""An overlapping first request must not see a half-loaded daily module."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading,unittest
from unittest.mock import patch
from test_api import app

class DailyInitializationTest(unittest.TestCase):
    def test_publish_only_a_fully_initialized_shared_module(self):
        entered=threading.Event();release=threading.Event();second_started=threading.Event();second_returned=threading.Event()
        def load(module):
            entered.set()
            if not release.wait(2):raise AssertionError('Test loader was not released')
            module.ready=True
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=load))
        def second():
            second_started.set();result=app.daily_runtime()[0];second_returned.set();return result
        previous=app._daily_module;app._daily_module=None
        try:
            with patch.object(app.importlib.util,'spec_from_file_location',return_value=spec),patch.object(app.importlib.util,'module_from_spec',return_value=SimpleNamespace()),ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(app.daily_runtime)
                self.assertTrue(entered.wait(1));other=pool.submit(second)
                self.assertTrue(second_started.wait(1))
                try:self.assertFalse(second_returned.wait(.05),'A request saw a partly loaded module')
                finally:release.set()
                self.assertTrue(first.result()[0].ready)
                self.assertIs(first.result()[0],other.result())
        finally:release.set();app._daily_module=previous

if __name__=='__main__':unittest.main()
