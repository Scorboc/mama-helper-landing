"""Local age-tip worker; uses reviewed content, never paid AI generation."""
import json
import os
from pathlib import Path
import threading
import time
import daily_job

_thread = None


def deliver(app):
    db = app.DB()
    try:
        return daily_job.run(app, db, guidance_only=True)
    finally:
        db.close()


def start(app):
    global _thread
    if os.environ.get('APP_LOCAL') != '1' or os.environ.get('APP_LOCAL_PUSH_ENABLED') != '1':
        return None
    if not all(os.environ.get(key) for key in ('VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY', 'VAPID_SUBJECT')):
        return None
    if _thread and _thread.is_alive():
        return _thread

    def worker():
        while True:
            try:
                result = deliver(app)
            except Exception:
                # Push exceptions may include endpoints or credentials. Log counts only.
                result = {'generated': 0, 'delivered': 0, 'errors': 1}
            path = os.environ.get('APP_PUSH_STATUS_PATH')
            if path:
                try:
                    target = Path(path)
                    temporary = target.with_suffix('.tmp')
                    temporary.write_text(json.dumps({'checkedAt': int(time.time()), 'mode': 'age-catalog', **result}), encoding='utf-8')
                    temporary.replace(target)
                except OSError:
                    pass
            time.sleep(60)

    _thread = threading.Thread(target=worker, name='mama-age-push', daemon=True)
    _thread.start()
    return _thread
