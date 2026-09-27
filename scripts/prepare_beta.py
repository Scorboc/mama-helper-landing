"""Create private credentials locally; only hashes are provisioned to the VM."""
import csv, hashlib, json, secrets
from pathlib import Path

out=Path(__file__).resolve().parents[3]/'outputs'
out.mkdir(exist_ok=True)
credentials=out/'beta-50-credentials.csv'
manifest=out/'beta-50-hashes.json'
if credentials.exists() or manifest.exists():
    raise SystemExit('Existing beta files preserved; do not regenerate.')
rows=[]; hashes=[]
for number in range(1,51):
    password=secrets.token_urlsafe(18); recovery=secrets.token_urlsafe(24)
    uid=secrets.token_hex(16); salt=secrets.token_hex(16)
    email=f'beta-{number:02d}@mama-helper.local'
    # Matches the application password_hash format and UTF-8 salt handling.
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
    rows.append([number,'https://mama-helper-158-160-188-235.sslip.io/account',email,password,recovery])
    hashes.append(dict(id=uid,email=email,password_hash=salt+'$'+digest,recovery_hash=hashlib.sha256(recovery.encode()).hexdigest()))
with credentials.open('w',encoding='utf-8-sig',newline='') as file:
    writer=csv.writer(file,delimiter=';');writer.writerow(['Номер','Сайт','Логин','Пароль','Код восстановления']);writer.writerows(rows)
manifest.write_text(json.dumps(hashes),encoding='utf-8')
print('Prepared 50 individual accounts; credentials saved locally, not printed.')
