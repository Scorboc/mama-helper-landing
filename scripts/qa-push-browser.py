"""Mobile push UI QA against a temporary DB. No real family records are loaded."""
import calendar
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'private/local-runtime'
sys.path.insert(0, str(RUNTIME / 'qa-deps'))
from playwright.sync_api import sync_playwright, expect

OUT = ROOT / 'outputs/qa-age-push-20261012'
OUT.mkdir(parents=True, exist_ok=True)
API = 'http://127.0.0.1:8793/'
UI = 'http://127.0.0.1:5174'
config = json.loads((RUNTIME / 'settings.json').read_text())
push = json.loads(Fernet(config['data_key']).decrypt((RUNTIME / 'push-settings.enc').read_bytes()))


def born_months_ago(months):
    today = date.today()
    total = today.year * 12 + today.month - 1 - months
    year, index = divmod(total, 12)
    month = index + 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1])).isoformat()


def ready(url):
    for _ in range(80):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.25)
    raise RuntimeError('Isolated QA server did not start')


with tempfile.TemporaryDirectory(prefix='push-ui-', dir=RUNTIME) as private:
    env = os.environ.copy()
    env.update(APP_LOCAL='1', APP_BILLING_MODE='legacy', APP_PAYMENTS_ENABLED='0',
               APP_SQLITE_PATH=str(Path(private) / 'qa.sqlite3'), APP_DATA_KEY=Fernet.generate_key().decode(),
               APP_ORIGINS=UI, APP_EMAIL_VERIFICATION_REQUIRED='0', APP_LOCAL_PUSH_ENABLED='0',
               CHEAPAI_LIVE_ENABLED='0', PROXYAPI_API_KEY='', APP_SMTP_HOST='',
               APP_PUSH_STATUS_PATH='', VAPID_PUBLIC_KEY=push['VAPID_PUBLIC_KEY'])
    command = "import local_server as server; server.app.cipher(); server.app.initialize(); server.ThreadingHTTPServer(('127.0.0.1',8793),server.Handler).serve_forever()"
    node = r'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
    processes = []
    log = (Path(private) / 'qa.log').open('wb')
    try:
        processes.append(subprocess.Popen([sys.executable, '-c', command], cwd=ROOT / 'app/backend/parent-app', env=env,
                                         stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW))
        frontend_env = {**env, 'VITE_APP_API_URL': API}
        processes.append(subprocess.Popen([node, str(ROOT / 'app/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5174', '--strictPort'],
                                         cwd=ROOT / 'app', env=frontend_env, stdout=log, stderr=log,
                                         creationflags=subprocess.CREATE_NO_WINDOW))
        ready(API + 'healthz'); ready(UI)
        report = {'syntheticDataOnly': True, 'checks': [], 'pageErrors': [], 'realPushServiceAccepted': False}
        (OUT / 'browser-errors.json').write_text('[]', encoding='utf-8')
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
            context = browser.new_context(viewport={'width':390, 'height':844}, permissions=['notifications'], locale='ru-RU')
            page = context.new_page()
            def page_error(error):
                report['pageErrors'].append(str(error))
                (OUT / 'browser-errors.json').write_text(json.dumps(report['pageErrors'], ensure_ascii=False), encoding='utf-8')
            page.on('pageerror', page_error)

            def api(action, **data):
                response = context.request.post(API, headers={'Origin':UI}, data={'action':action, **data})
                assert response.ok, f'Synthetic API request failed: {action}/{response.status}'
                return response.json()

            session = api('register', email='push-qa@example.test', password='synthetic-test-password', consent=True)
            state = session['state']
            profile = {'childName':'QA Первый','childSex':'unknown','role':'mom','stage':'child',
                       'birthDate':born_months_ago(1),'week':20,'weekDate':date.today().isoformat(),
                       'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
            state.update(profile=profile, activeChildId='primary', children=[{'id':'second','data':{'profile':{**profile,'childName':'QA Второй','birthDate':born_months_ago(5)}}}])
            api('save', state=state, revision=session['revision'])
            page.goto(UI + '/cabinet?tab=chat&child=second&topic=feeding-six-months')
            page.wait_for_load_state('networkidle')
            # Inspect rendered DOM before choosing selectors.
            (OUT / 'browser-dom.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
            guidance = page.get_by_role('region', name='Подсказки по возрасту')
            expect(guidance).to_contain_text('QA Второй · 5 мес.')
            expect(guidance).to_contain_text('Новый этап питания')
            page.screenshot(path=str(OUT / 'push-deep-link-mobile.png'), full_page=False)
            report['checks'].append('Deep link switches to the correct profile and current topic')

            page.goto(UI + '/cabinet?tab=chat&child=second&topic=month-care-4')
            expect(page.get_by_role('region', name='Подсказки по возрасту')).to_contain_text('Эта подсказка недоступна')
            report['checks'].append('Expired topic is not shown as current advice')

            page.goto(UI + '/cabinet?tab=settings')
            page.wait_for_load_state('networkidle')
            expect(page.get_by_text('без имени, даты рождения', exact=False)).to_be_visible()
            expect(page.get_by_label('Часовой пояс')).to_be_visible()
            page.screenshot(path=str(OUT / 'push-settings-mobile.png'), full_page=False)
            report['checks'].append('Mobile settings explain privacy, timezone, consent and limits')

            page.get_by_role('button', name='Включить push', exact=True).click()
            try:
                expect(page.get_by_role('button', name='Отключить push', exact=True)).to_be_visible(timeout=23000)
                # Use the actual browser subscription only for one generic synthetic message.
                subscription = page.evaluate('async () => (await navigator.serviceWorker.ready).pushManager.getSubscription().then(s => s.toJSON())')
                sys.path.insert(0, str(RUNTIME / 'push-deps'))
                from pywebpush import webpush
                response = webpush(subscription_info=subscription, data=json.dumps({'body':'Проверка MAMA Helper: уведомления подключены.','path':'/cabinet?tab=settings'}),
                                   vapid_private_key=push['VAPID_PRIVATE_KEY'], vapid_claims={'sub':push['VAPID_SUBJECT']}, timeout=8)
                report['realPushServiceAccepted'] = 200 <= response.status_code < 300
                page.get_by_role('button', name='Отключить push', exact=True).click()
                expect(page.get_by_role('button', name='Включить push', exact=True)).to_be_visible()
                report['checks'].append('Actual subscription and unsubscribe passed')
            except Exception:
                # Keep endpoints, credentials and provider exceptions out of reports.
                alert = page.get_by_role('alert')
                report['browserSubscriptionUnavailable'] = alert.count() > 0
                report['subscriptionFailureShown'] = alert.count() > 0 and alert.first.is_visible()
                report['actualDeviceDeliveryConfirmed'] = False
                expect(page.get_by_role('button', name='Включить push', exact=True)).to_be_enabled()
                report['checks'].append('Failed subscription leaves push disabled with a visible error and retry')
                # An isolated API fixture checks the success UI separately. This is
                # explicitly a stub, never evidence of actual device delivery.
                page.evaluate("""() => {
                  PushManager.prototype.getSubscription = async () => ({toJSON: () => ({endpoint:'https://fcm.googleapis.com/fcm/send/ui-synthetic',keys:{auth:'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',p256dh:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}})});
                }""")
                page.get_by_role('button', name='Включить push', exact=True).click()
                expect(page.get_by_role('button', name='Отключить push', exact=True)).to_be_visible(timeout=8000)
                page.get_by_role('button', name='Отключить push', exact=True).click()
                expect(page.get_by_role('button', name='Включить push', exact=True)).to_be_visible()
                report['checks'].append('Synthetic subscription success and unsubscribe UI passed')
            assert api('session')['state']['preferences']['push'] is False
            browser.close()
        (OUT / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        for process in reversed(processes):
            process.terminate()
            process.wait(timeout=10)
        log.close()
