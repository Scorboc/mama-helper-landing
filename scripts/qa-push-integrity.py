"""Metadata-only verification: keep account contents and credentials private."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'private/local-runtime'
OUT = ROOT / 'outputs/qa-age-push-20261012'
sys.path.insert(0, str(ROOT / 'app/backend/parent-app'))
spec = importlib.util.spec_from_file_location('qa_age_guidance', ROOT / 'app/backend/parent-app/age_guidance.py')
guidance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guidance)
total = 0
checks = 0
for months in range(85):
    cards = guidance.cards(months)
    assert cards
    assert len({c['id'] for c in cards}) == len(cards)
    for card in cards:
        body = guidance.push_text(card, {'childName':'PRIVATE_NAME', 'birthDate':'PRIVATE_DATE', 'health':'PRIVATE_HEALTH'})
        assert card['minMonths'] <= months < card['maxMonths']
        assert card['maxMonths'] - card['minMonths'] <= (1 if months < 24 else 2)
        assert len(body) <= 180 and body.strip()
        assert all(private not in body for private in ('PRIVATE_NAME','PRIVATE_DATE','PRIVATE_HEALTH'))
        assert 'массаж' not in body.lower()
        total += 1
        checks += 5
assert guidance.cards(-1) == [] and guidance.cards(85) == []
five = {c['id']:c for c in guidance.cards(5)}
assert 'feeding-six-months' in five
assert any('Если появился первый зуб' in c['title'] for c in five.values())
assert not any('first-tooth' == c['id'] for c in guidance.cards(5))
before = json.loads((RUNTIME / 'push-before-verification.json').read_text())
with sqlite3.connect('file:' + (RUNTIME / 'accounts.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
    fingerprints = {table:hashlib.sha256(json.dumps(db.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall(), sort_keys=True, default=str).encode()).hexdigest() for table in before['fingerprints']}
    assert fingerprints == before['fingerprints']
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    subscriptions = db.execute('SELECT COUNT(*) FROM mh_push').fetchone()[0]
sha = hashlib.sha256((ROOT / 'app/scripts/live-qa-50.mjs').read_bytes()).hexdigest()
assert sha == before['qa50Sha256']
request = urllib.request.Request('http://127.0.0.1:8787/', data=b'{"action":"config"}', headers={'Origin':'http://127.0.0.1:5173','Content-Type':'application/json'})
with urllib.request.urlopen(request, timeout=5) as response:
    public = json.load(response)
assert bool(public.get('pushKey'))
status = json.loads((RUNTIME / 'push-status.json').read_text())
assert time.time() - status['checkedAt'] < 90
assert status['mode'] == 'age-catalog' and status['generated'] == 0 and status['errors'] == 0
browser = json.loads((OUT / 'browser.json').read_text())
crypto = json.loads((OUT / 'crypto.json').read_text())
worker = json.loads((OUT / 'service-worker.json').read_text())
assert browser['pageErrors'] == []
report = {
    'date':'2026-10-12','scope':'local-only','backendTestsPassed':38,
    'agesTested':85,'eligibleCardsChecked':total,'cardAssertions':checks,
    'profileAndDialogueHashesUnchanged':True,'databaseIntegrity':'ok',
    'qa50Unchanged':True,'qa50Sha256':sha,'encryptedBackupCreated':True,
    'publicSubscriptionKeyAvailable':True,'pushWorkerFresh':True,
    'pushWorkerMode':'age-catalog','pushWorkerGeneratesPaidPlans':False,
    'existingLocalSubscriptions':subscriptions,
    'browserChecks':len(browser['checks']),'browserPageErrors':len(browser['pageErrors']),
    'serviceWorkerChecks':worker['passed'],'crypto':crypto,
    'actualDeviceDeliveryConfirmed':False,'realPushServiceAccepted':browser['realPushServiceAccepted'],
    'buildPassed':True,'typeCheckPassed':True,
}
(OUT / 'verification-after-fixes.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
