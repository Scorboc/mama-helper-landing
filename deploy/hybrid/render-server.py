"""Prepare Linux configuration locally; credentials never reach stdout or Cloudflare."""
import argparse
import json
import os
from pathlib import Path
import sys
from cryptography.fernet import Fernet
from prepare import APP, ROOT, LOCAL, N8N, domain_origins


def environment_file(values):
    lines = []
    for key, value in sorted(values.items()):
        value = str(value)
        if '\n' in value or '\r' in value or '\x00' in value:
            raise ValueError('Environment values must contain no control characters')
        lines.append(key + '="' + value.replace('\\', '\\\\').replace('"', '\\"') + '"')
    return '\n'.join(lines) + '\n'


def render(domain, output, test=False):
    frontend, api = domain_origins(domain, test)
    output = output.resolve()
    if not output.is_relative_to((ROOT / 'private').resolve()) or output.exists():
        raise ValueError('Use a new directory within the private workspace')
    output.mkdir(parents=True, mode=0o700)
    sys.path.insert(0, str(LOCAL))
    from runtime_env import load
    config = json.loads((LOCAL / 'settings.json').read_text(encoding='utf-8'))
    source = load(config)
    prefixes = ('APP_', 'AI_', 'PROXYAPI_', 'CHEAPAI_', 'CHEAP_AI_', 'YANDEX_', 'VAPID_')
    env = {k: str(v) for k, v in source.items() if k.startswith(prefixes)}
    for name in ('APP_LOCAL_PUSH_ENABLED', 'APP_MAIL_LOCAL_DIR', 'APP_MAIL_DRIVER', 'PYTHONPATH'):
        env.pop(name, None)
    env.update(APP_LOCAL='0', APP_DB_DRIVER='sqlite', APP_COOKIE_SECURE='1', APP_COOKIE_CROSS_SITE='0',
               APP_ORIGINS=frontend, APP_PUBLIC_URL=frontend,
               APP_SQLITE_PATH='/srv/mama/data/local-runtime/accounts.sqlite3',
               APP_AI_BUDGET_PATH='/srv/mama/data/local-runtime/ai-budget.sqlite3',
               AI_POLICY_FILE='/srv/mama/data/local-runtime/ai-policy.json',
               APP_OPS_PATH='/srv/mama/data/local-runtime/operations.sqlite3',
               APP_OPS_ROOT='/srv/mama/data/local-runtime/operations',
               APP_FEEDBACK_REVIEW_ROOT='/srv/mama/data/local-runtime/feedback-review',
               APP_PUSH_STATUS_PATH='/srv/mama/data/local-runtime/push-status.json',
               APP_WEB_ROOT='/srv/mama/frontend', APP_MONITOR_URL=frontend,
               APP_BACKUP_KEY_FILE='/srv/mama/data/n8n/backup.key',
               MAMA_AUTOMATION_ROOT='/srv/mama/data/n8n')
    settings = json.loads((N8N / 'settings.json').read_text(encoding='utf-8'))
    env['MAMA_AUTOMATION_TOKEN'] = settings['bridgeToken']
    for key, value in env.items():
        if ':\\' in value or value.startswith('http://localhost:5173') or value.startswith('http://127.0.0.1:5173'):
            raise ValueError('Unmapped local runtime setting')
    n8n = dict(N8N_USER_FOLDER='/srv/mama/data/n8n/state', N8N_ENCRYPTION_KEY=settings['encryptionKey'],
               N8N_LISTEN_ADDRESS='127.0.0.1', N8N_HOST='127.0.0.1', N8N_PORT='5678', N8N_PROTOCOL='http',
               N8N_EDITOR_BASE_URL='http://127.0.0.1:5678', N8N_WEBHOOK_URL='http://127.0.0.1:5678/',
               N8N_SECURE_COOKIE='false', N8N_DIAGNOSTICS_ENABLED='false', N8N_PERSONALIZATION_ENABLED='false',
               N8N_VERSION_NOTIFICATIONS_ENABLED='false', N8N_TEMPLATES_ENABLED='false',
               N8N_PUBLIC_API_DISABLED='true', N8N_BLOCK_ENV_ACCESS_IN_NODE='true',
               N8N_COMMUNITY_PACKAGES_ENABLED='false', N8N_UNVERIFIED_PACKAGES_ENABLED='false',
               N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES='true', N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS='true',
               EXECUTIONS_DATA_PRUNE='true', EXECUTIONS_DATA_MAX_AGE='168', EXECUTIONS_DATA_PRUNE_MAX_COUNT='1000',
               EXECUTIONS_DATA_SAVE_ON_SUCCESS='none', EXECUTIONS_DATA_SAVE_ON_ERROR='all',
               GENERIC_TIMEZONE='Europe/Saratov', TZ='Europe/Saratov', N8N_LOG_LEVEL='warn',
               NODE_OPTIONS='--max-old-space-size=768',
               NODES_EXCLUDE=json.dumps(['n8n-nodes-base.executeCommand', 'n8n-nodes-base.ssh',
                                        'n8n-nodes-base.readWriteFile', 'n8n-nodes-base.readBinaryFile',
                                        'n8n-nodes-base.writeBinaryFile']))
    for name, values in (('app.env', env), ('n8n.env', n8n)):
        path = output / name
        path.write_text(environment_file(values), encoding='utf-8')
        path.chmod(0o600)
    template = (Path(__file__).parent / 'nginx-api.template').read_text(encoding='utf-8')
    (output / 'nginx-api.conf').write_text(template.replace('@API_HOST@', api.removeprefix('https://')), encoding='utf-8')
    service = (Path(__file__).parent / 'systemd-service.template').read_text(encoding='utf-8')
    jobs = {'api': ('/srv/mama/venv/bin/python /srv/mama/app/backend/parent-app/production_server.py', 'app', '1G'),
            'operations': ('/srv/mama/venv/bin/python /srv/mama/app/backend/parent-app/ops_server.py', 'app', '512M'),
            'bridge': ('/srv/mama/venv/bin/python /srv/mama/app/backend/parent-app/automation_bridge.py', 'app', '512M'),
            'n8n': ('/usr/bin/node /srv/mama/n8n-runtime/node_modules/n8n/bin/n8n start', 'n8n', '1200M')}
    for name, (command, environment, memory) in jobs.items():
        text = service.replace('@NAME@', name).replace('@COMMAND@', command).replace('@ENV@', environment).replace('@MEMORY@', memory)
        (output / ('mama-' + name + '.service')).write_text(text, encoding='utf-8')
    (output / 'mama-reminders.service').write_text(
        '[Unit]\nDescription=MAMA consented age reminders\nAfter=network-online.target\n'
        '[Service]\nType=oneshot\nUser=mama\nGroup=mama\nUMask=0077\n'
        'WorkingDirectory=/srv/mama/app/backend/parent-app\nEnvironmentFile=/etc/mama/app.env\n'
        'ExecStart=/srv/mama/venv/bin/python /srv/mama/app/backend/parent-app/daily_job.py\n'
        'NoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\nProtectHome=true\nReadWritePaths=/srv/mama/data\n', encoding='utf-8')
    (output / 'mama-reminders.timer').write_text(
        '[Unit]\nDescription=MAMA reminder schedule\n[Timer]\nOnCalendar=*:0/10\n'
        'Persistent=false\nRandomizedDelaySec=20\n[Install]\nWantedBy=timers.target\n', encoding='utf-8')
    result = {'created': True, 'testDomain': test, 'published': False, 'cookieSameSite': 'Lax',
              'apiOrigin': api, 'frontendOrigin': frontend, 'sameSite': True,
              'credentialsKeptPrivate': True, 'originalDataKeyPreserved': env['APP_DATA_KEY'] == config['data_key'],
              'originalN8nKeyPreserved': n8n['N8N_ENCRYPTION_KEY'] == settings['encryptionKey'],
              'emailConfigured': all(env.get(k) for k in ('APP_SMTP_HOST', 'APP_SMTP_USER', 'APP_SMTP_PASSWORD', 'APP_EMAIL_FROM')),
              'paymentsEnabled': env.get('APP_PAYMENTS_ENABLED') == '1',
              'vapidConfigured': all(env.get(k) for k in ('VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY', 'VAPID_SUBJECT'))}
    (output / 'status.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    try:
        render(args.domain, args.output, args.test)
    except Exception as exc:
        print(json.dumps({'ok': False, 'errorType': type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
