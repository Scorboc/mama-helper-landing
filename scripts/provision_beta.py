"""Run on VM with app env; import hashes without passwords or resetting accounts."""
import importlib.util, json, sys, time
from pathlib import Path
spec=importlib.util.spec_from_file_location('app',Path(sys.argv[1])/'index.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
records=json.loads(Path(sys.argv[2]).read_text())
assert len(records)==50 and len({r['id'] for r in records})==50
db=app.DB();created=0
try:
    for r in records:
        previous=db.query('SELECT id FROM mh_users WHERE email=?',(r['email'],)).fetchone()
        if previous:
            assert previous[0]==r['id'], 'Existing login belongs to another account; stopping'
            continue
        db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',(r['id'],r['email'],r['password_hash'],r['recovery_hash'],int(time.time()),'test-v1'))
        db.query('INSERT INTO mh_state VALUES(?,?,0)',(r['id'],app.seal(app.blank_state())))
        created+=1
    db.conn.commit()
    print(json.dumps({'created':created,'individual_beta_accounts':50}))
finally: db.close()
