"""Public operator details and contract receipts. Never substitute a checkbox for written health consent."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

TERMS_VERSION = 'account-2026-10-12'
OFFER_VERSION = 'offer-480-300-2026-10-12'
POLICY_VERSION = 'privacy-2026-10-12'


def public():
    operator = {name: os.environ.get(env, '').strip() for name, env in {
        'name': 'APP_OPERATOR_NAME', 'inn': 'APP_OPERATOR_INN',
        'address': 'APP_OPERATOR_ADDRESS', 'email': 'APP_SUPPORT_EMAIL',
    }.items()}
    ready = (all(operator.values()) and bool(re.fullmatch(r'\d{12}', operator['inn']))
             and os.environ.get('APP_DATA_COUNTRY') == 'RU'
             and os.environ.get('APP_LEGAL_APPROVED') == '1')
    return {'operator': operator, 'documentsReady': bool(ready),
            'termsVersion': TERMS_VERSION, 'offerVersion': OFFER_VERSION,
            'policyVersion': POLICY_VERSION}


def require_public_ready(app):
    if os.environ.get('APP_LOCAL') != '1' and not public()['documentsReady']:
        raise app.AppError(503, 'Приём новых пользователей и оплаты пока закрыт: владелец готовит документы сервиса.')


def require_health_authorization(app, db, uid):
    if os.environ.get('APP_LOCAL') == '1':
        return
    row = db.query('SELECT document_hash,method,verified_at,revoked_at FROM mh_health_consents WHERE user_id=?',(uid,)).fetchone()
    if not row or not re.fullmatch(r'[a-f0-9]{64}',row[0]) or row[1] not in ('signed-paper','verified-electronic-signature') or not row[2] or row[3]:
        raise app.AppError(403,'Для персональных функций со сведениями о здоровье необходимо отдельное надлежащее согласие. Способ оформления уточните у владельца в разделе «Данные и обращения».')


def receipt(app, db, uid, kind, version):
    # Proof of contract acceptance, not consent to medical data or advertising.
    documents = json.loads(Path(__file__).with_name('legal_documents.json').read_text(encoding='utf-8'))
    document = documents[kind]
    if document['version'] != version:
        raise app.AppError(503, 'Редакция документа не совпадает. Обратитесь к владельцу.')
    content = json.dumps({'document': document, 'operator': public()['operator']}, ensure_ascii=False, sort_keys=True)
    db.query('INSERT INTO mh_contract_receipts(user_id,kind,version,accepted_at,document_hash,document_text) VALUES(?,?,?,?,?,?)',
             (uid, kind, version, int(time.time()), hashlib.sha256(content.encode()).hexdigest(), content))
