"""Test an isolated static release with a synthetic unavailable API."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright


def run(directory, output, chrome):
    output.mkdir(parents=True, exist_ok=True)
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            requested = urlsplit(self.path).path.lstrip('/')
            if not (directory / requested).is_file(): self.path = '/index.html'
            super().do_GET()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    results, requests, errors = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=str(chrome), headless=True)
            context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            def network(route):
                url = route.request.url
                if url.startswith(base + '/'):
                    route.continue_(); return
                if url == 'https://api.mama.test/api':
                    requests.append({'destination': 'synthetic-api', 'method': route.request.method})
                    headers = {'Access-Control-Allow-Origin': base, 'Access-Control-Allow-Credentials': 'true',
                               'Access-Control-Allow-Headers': 'content-type, authorization',
                               'Access-Control-Allow-Methods': 'POST, OPTIONS'}
                    if route.request.method == 'OPTIONS':
                        route.fulfill(status=204, headers=headers); return
                    body = route.request.post_data_json
                    if body.get('action') == 'config':
                        route.fulfill(status=200, content_type='application/json', headers=headers,
                                      body=json.dumps({'ok': True, 'emailConfigured': False, 'emailVerificationRequired': False,
                                                       'pushKey': '', 'chatConfigured': False, 'billing': {'mode': 'paid', 'paymentsEnabled': False},
                                                       'legal': {'documentsReady': False, 'operator': {}, 'termsVersion': 'account-2026-10-12'}}))
                    else:
                        route.fulfill(status=503, content_type='application/json', headers=headers,
                                      body=json.dumps({'error': 'Сервис временно недоступен. Попробуйте позже.'}, ensure_ascii=False))
                    return
                requests.append({'destination': 'unexpected-external', 'method': route.request.method})
                route.abort()
            context.route('**/*', network)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for route in ('/', '/account?mode=login', '/first-aid', '/privacy', '/offer', '/guide'):
                page.goto(base + route)
                page.wait_for_load_state('networkidle')
                page.locator('h1').first.wait_for(state='visible')
                text = page.locator('body').inner_text()
                assert 'Не удалось открыть страницу' not in text
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2')
                if route == '/first-aid':
                    assert '112' in text
                    page.screenshot(path=str(output / 'first-aid-api-offline.png'), full_page=True)
                results.append({'route': route, 'rendered': True, 'horizontalOverflow': False})
            page.goto(base + '/account?mode=login')
            page.wait_for_load_state('networkidle')
            labels = [{'label': label.inner_text()} for label in page.locator('label').all()]
            (output / 'account-labels.json').write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding='utf-8')
            page.get_by_label('Электронная почта', exact=False).fill('synthetic@example.test')
            page.get_by_label('Пароль', exact=True).fill('synthetic-long-password')
            page.get_by_role('button', name='Войти', exact=True).click()
            page.get_by_role('alert').filter(has_text='Сервис временно недоступен').wait_for(state='visible')
            page.get_by_role('link', name='Срочная помощь · 112').click()
            page.wait_for_load_state('networkidle')
            assert '112' in page.locator('body').inner_text()
            results.append({'loginFailureVisible': True, 'firstAidAccessibleAfterFailure': True})
            assert not errors
            assert not any(r['destination'] == 'unexpected-external' for r in requests)
            browser.close()
        result = {'checks': results, 'pageErrors': errors, 'unexpectedExternalRequests': 0,
                  'realUserDataUsed': False, 'realAiCalls': 0, 'publicHttpsVerified': False,
                  'safariVerified': False, 'scope': 'local static build and synthetic unavailable API'}
        (output / 'browser-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'ok': True, 'checks': len(results), 'unexpectedExternalRequests': 0, 'realAiCalls': 0}))
    finally:
        server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--chrome', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory.resolve(), args.output.resolve(), args.chrome)
