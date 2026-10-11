"""Real API against a temporary encrypted synthetic database. No AI charges."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
from cryptography.fernet import Fernet

if __name__ == '__main__':
    backend = Path(__file__).resolve().parents[1] / 'backend' / 'parent-app'
    sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix='mama-jtbd-qa-') as directory:
        os.environ.update(APP_LOCAL='1', APP_SQLITE_PATH=str(Path(directory) / 'synthetic.db'),
                          APP_DATA_KEY=Fernet.generate_key().decode(),
                          APP_ORIGINS='http://127.0.0.1:5173,http://localhost:5173',
                          CHEAPAI_LIVE_ENABLED='0')
        # Test process never uses inherited provider credentials or production analytics.
        for name in ('PROXYAPI_API_KEY','YANDEX_API_KEY','YANDEX_FOLDER_ID','YANDEX_USE_METADATA_IAM',
                     'CHEAPAI_PROXY_TOKEN','CHEAPAI_API_KEY','CHEAP_AI_API_KEY','VAPID_PUBLIC_KEY','VAPID_PRIVATE_KEY',
                     'APP_OPS_PATH','APP_OPS_HASH_KEY','MAMA_OPS_DIR','OPS_LOG_PATH'):
            os.environ.pop(name, None)
        runpy.run_path(str(backend / 'local_server.py'), run_name='__main__')
