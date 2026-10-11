"""Import local SMTP .env or JSON into an encrypted private file; print no secrets."""
import argparse
import json
from pathlib import Path
from cryptography.fernet import Fernet

FIELDS={'APP_SMTP_HOST','APP_SMTP_PORT','APP_SMTP_SECURITY','APP_SMTP_USER','APP_SMTP_PASSWORD','APP_EMAIL_FROM'}
parser=argparse.ArgumentParser(description='Save local SMTP settings without exposing credentials.')
parser.add_argument('--file',required=True,help='Absolute path to SMTP .env or JSON.')
args=parser.parse_args()
source=Path(args.file).expanduser().resolve()
text=source.read_text(encoding='utf-8-sig')
if source.suffix.lower()=='.json':
    values=json.loads(text)
else:
    values={}
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        name,separator,value=line.partition('=')
        if not separator:raise SystemExit('Expected KEY=value SMTP settings.')
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
        values[name.strip()]=value
values={key:str(value) for key,value in values.items() if key in FIELDS}
if any(not values.get(key) for key in ('APP_SMTP_HOST','APP_SMTP_USER','APP_SMTP_PASSWORD','APP_EMAIL_FROM')):
    raise SystemExit('Missing required SMTP fields.')
if any('\r' in value or '\n' in value for value in values.values()):raise SystemExit('Invalid SMTP setting.')
values.setdefault('APP_SMTP_SECURITY','ssl');values.setdefault('APP_SMTP_PORT','465')
try:port=int(values['APP_SMTP_PORT'])
except ValueError:raise SystemExit('Use a valid numeric SMTP port.')
if values['APP_SMTP_SECURITY'] not in ('ssl','starttls') or not 1<=port<=65535:
    raise SystemExit('Use valid SMTP port and ssl/starttls.')
root=Path(__file__).resolve().parents[2]
private=root/'private/local-runtime'
config=json.loads((private/'settings.json').read_text(encoding='utf-8'))
cipher=Fernet(config['data_key'])
target=private/'mail-settings.enc'
if target.exists():(private/'mail-settings.previous.enc').write_bytes(target.read_bytes())
target.write_bytes(cipher.encrypt(json.dumps(values).encode()))
print('SMTP settings saved encrypted. Restart the owned local account service to apply.')
