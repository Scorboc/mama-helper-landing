"""Owner-approved text, bundled with the backend; never fetched from a network."""
import hashlib
import json
import re
from pathlib import Path

VERSION = 'mama-reviewed-20261013-v13'
DIRECTORY = Path(__file__).with_name('prompts')
MANIFEST = json.loads((DIRECTORY / 'reviewed-20261013-v13.json').read_text(encoding='utf-8'))


def approved_part(name):
    item = MANIFEST['parts'][name]
    filename = item['file']
    if Path(filename).name != filename:
        raise RuntimeError('Approved instruction filename must be local.')
    data = (DIRECTORY / filename).read_bytes()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise RuntimeError('Approved AI instruction checksum does not match.')
    return data.decode('utf-8').replace('\r\n','\n').strip()


if MANIFEST['version'] != VERSION:
    raise RuntimeError('Approved AI instruction version does not match.')

CHAT_SYSTEM_PROMPT = approved_part('chat')
DAILY_SYSTEM_PROMPT = approved_part('daily')
# Push messages currently use local reviewed templates, not a generative model.
NOTIFICATION_RULES = approved_part('notification')


def section(number):
    return CHAT_SYSTEM_PROMPT.split(f'### {number}. ', 1)[1].split('\n### ', 1)[0].strip()


def reply_check(question):
    """Repeat only relevant approved rules after the long data block."""
    q = question.lower().replace('ё', 'е')
    # The full reviewed rules are already in the system instruction. Repeating
    # entire sections can crowd out the current journal and eligible catalogue.
    return approved_part('reply')
