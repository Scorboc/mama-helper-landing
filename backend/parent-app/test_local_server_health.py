"""Account monitor route must match the local automation probe."""
import http.client
import importlib.util
import json
import threading
import unittest
from pathlib import Path


class LocalServerHealthTest(unittest.TestCase):
    def test_healthz_matches_monitor_contract(self):
        spec = importlib.util.spec_from_file_location(
            'local_server_health_test', Path(__file__).with_name('local_server.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request('GET', '/healthz')
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Cache-Control'), 'no-store')
            self.assertTrue(json.loads(response.read())['ok'])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
