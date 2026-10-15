"""Synthetic mailbox ownership, single-use recovery and encrypted mail delivery."""
import json
from email import policy
from email.parser import BytesParser
import os
import re
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet
import index as app
import account_email
import mail_delivery


class AccountEmailTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='mama-email-test-')
        self.environment = dict(os.environ)
        os.environ.update(APP_LOCAL='1', APP_SQLITE_PATH=self.directory.name+'/synthetic.sqlite3',
                          APP_DATA_KEY=Fernet.generate_key().decode(), APP_ORIGINS='http://localhost:5173',
                          APP_MAIL_DRIVER='local', APP_MAIL_LOCAL_DIR=self.directory.name+'/mail',
                          APP_PUBLIC_URL='http://localhost:5173', APP_EMAIL_VERIFICATION_REQUIRED='1')
        for key in ('APP_OPS_PATH', 'APP_AI_BUDGET_PATH', 'AI_POLICY_FILE'):
            os.environ.pop(key, None)
        app.initialize()

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.environment)
        self.directory.cleanup()

    def call(self, action, cookie='', **data):
        response = app.handler({'httpMethod':'POST', 'headers':{'Origin':'http://localhost:5173',
            'Content-Type':'application/json', 'Cookie':cookie}, 'body':json.dumps({'action':action, **data}),
            'requestContext':{'identity':{'sourceIp':'127.0.0.1'}}})
        return response, json.loads(response['body'])

    def register(self, email='synthetic@example.test'):
        response, body = self.call('register', email=email, password='original-long-password', consent=True, adult=True, termsAccepted=True, termsVersion='account-2026-10-12')
        self.assertEqual(response['statusCode'], 200)
        return response['headers']['Set-Cookie'].split(';')[0], body

    def token(self, kind='verify', uid=None):
        db=app.DB()
        try:
            query="SELECT encrypted_message FROM mh_email_outbox WHERE kind=? AND status='pending'"
            params=(kind,)
            if uid: query+=' AND user_id=?'; params+=(uid,)
            row=db.query(query,params).fetchone()
            return re.search(r'#token=([A-Za-z0-9_-]+)', app.unseal(row[0])['text']).group(1)
        finally: db.close()

    def verify(self):
        _, account = self.register()
        self.assertEqual(self.call('email-verify',token=self.token())[0]['statusCode'],200)
        response,_=self.call('login',email=account['user']['email'],password='original-long-password')
        return response['headers']['Set-Cookie'].split(';')[0],account

    def test_registration_requires_confirmation_without_changing_existing_users(self):
        cookie, account=self.register()
        self.assertTrue(account['user']['emailVerificationRequired'])
        self.assertFalse(account['user']['emailVerified'])
        self.assertEqual(self.call('care-list',cookie)[0]['statusCode'],403)
        self.assertEqual(self.call('save',cookie,state=account['state'],revision=0)[0]['statusCode'],403)
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],200)
        token=self.token()
        db=app.DB()
        try:
            stored=db.query('SELECT token_hash FROM mh_email_tokens').fetchone()[0]
            self.assertNotEqual(stored,token)
            self.assertNotIn(token,db.query('SELECT encrypted_message FROM mh_email_outbox').fetchone()[0])
        finally:db.close()
        result,_=self.call('email-verify',token=token)
        self.assertEqual(result['statusCode'],200)
        self.assertIn('Max-Age=0',result['headers']['Set-Cookie'])
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],401)
        self.assertEqual(self.call('email-verify',token=token)[0]['statusCode'],400)
        login,payload=self.call('login',email=account['user']['email'],password='original-long-password')
        self.assertEqual(login['statusCode'],200);self.assertTrue(payload['user']['emailVerified'])

    def test_unknown_unconfirmed_legacy_and_verified_requests_have_identical_responses(self):
        _,account=self.verify()
        verified=self.call('email-request-reset',email=account['user']['email'])
        unknown=self.call('email-request-reset',email='absent@example.test')
        os.environ['APP_EMAIL_VERIFICATION_REQUIRED']='0'
        self.register('legacy@example.test')
        legacy=self.call('email-request-reset',email='legacy@example.test')
        self.assertEqual(verified[1],unknown[1]);self.assertEqual(verified[1],legacy[1])
        db=app.DB()
        try:self.assertEqual(db.query("SELECT count(*) FROM mh_email_outbox WHERE kind='reset'").fetchone()[0],1)
        finally:db.close()

    def test_reset_preserves_state_revokes_sessions_rotates_code_and_does_not_login(self):
        cookie,account=self.verify()
        state=account['state'];state['messages']=[{'id':str(i),'role':'user' if i%2==0 else 'assistant','text':'Synthetic history'} for i in range(100)]
        self.assertEqual(self.call('save',cookie,state=state,revision=0)[0]['statusCode'],200)
        self.call('email-request-reset',email=account['user']['email'])
        token=self.token('reset')
        response,result=self.call('email-reset',token=token,password='changed-long-password')
        self.assertEqual(response['statusCode'],200);self.assertIn('Max-Age=0',response['headers']['Set-Cookie'])
        self.assertNotEqual(result['recoveryCode'],account['recoveryCode'])
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],401)
        self.assertEqual(self.call('email-reset',token=token,password='changed-again-password')[0]['statusCode'],400)
        self.assertEqual(self.call('login',email=account['user']['email'],password='original-long-password')[0]['statusCode'],401)
        response,payload=self.call('login',email=account['user']['email'],password='changed-long-password')
        self.assertEqual(response['statusCode'],200);self.assertEqual(payload['state'],state);self.assertEqual(payload['revision'],1)

    def test_new_unconfirmed_account_can_reclaim_mailbox_without_old_password(self):
        cookie,account=self.register()
        self.call('email-request-reset',email=account['user']['email'])
        response,_=self.call('email-reset',token=self.token('reset'),password='mailbox-owner-password')
        self.assertEqual(response['statusCode'],200)
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],401)
        _,payload=self.call('login',email=account['user']['email'],password='mailbox-owner-password')
        self.assertTrue(payload['user']['emailVerified'])

    def test_expired_and_wrong_purpose_links_are_rejected_without_consuming_valid_link(self):
        cookie,account=self.verify();self.call('email-request-reset',email=account['user']['email'])
        token=self.token('reset')
        self.assertEqual(self.call('email-verify',token=token)[0]['statusCode'],400)
        self.assertEqual(self.call('email-reset',token=token,password='short')[0]['statusCode'],400)
        db=app.DB()
        try:db.query('UPDATE mh_email_tokens SET expires_at=?',(int(time.time())-1,));db.conn.commit()
        finally:db.close()
        self.assertEqual(self.call('email-reset',token=token,password='new-long-password')[0]['statusCode'],400)
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],200)

    def test_resend_supersedes_previous_link_and_is_limited(self):
        cookie,_=self.register();old=self.token()
        self.assertEqual(self.call('email-resend',cookie)[0]['statusCode'],200)
        self.assertEqual(self.call('email-verify',token=old)[0]['statusCode'],400)
        for _ in range(2):self.assertEqual(self.call('email-resend',cookie)[0]['statusCode'],200)
        self.assertEqual(self.call('email-resend',cookie)[0]['statusCode'],429)

    def test_public_reset_requests_are_limited_even_for_missing_accounts(self):
        for _ in range(3):self.assertEqual(self.call('email-request-reset',email='absent@example.test')[0]['statusCode'],200)
        self.assertEqual(self.call('email-request-reset',email='absent@example.test')[0]['statusCode'],429)

    def test_password_change_invalidates_outstanding_links(self):
        cookie,account=self.verify();self.call('email-request-reset',email=account['user']['email']);token=self.token('reset')
        self.assertEqual(self.call('change-password',cookie,currentPassword='original-long-password',password='new-long-password')[0]['statusCode'],200)
        self.assertEqual(self.call('email-reset',token=token,password='reset-long-password')[0]['statusCode'],400)

    def test_concurrent_reset_has_exactly_one_winner(self):
        _,account=self.verify();self.call('email-request-reset',email=account['user']['email']);token=self.token('reset')
        entered,release=threading.Event(),threading.Event();original=app.password_hash
        def pause(value):
            if value=='first-new-password':entered.set();self.assertTrue(release.wait(5))
            return original(value)
        with patch.object(app,'password_hash',side_effect=pause),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.call,'email-reset',token=token,password='first-new-password')
            self.assertTrue(entered.wait(5))
            second=pool.submit(self.call,'email-reset',token=token,password='second-new-password')
            time.sleep(.2);release.set();statuses=[first.result(8)[0]['statusCode'],second.result(8)[0]['statusCode']]
        self.assertEqual(sorted(statuses),[200,400])

    def test_missing_mail_configuration_rolls_back_registration(self):
        os.environ['APP_MAIL_DRIVER']='smtp'
        for name in ('APP_SMTP_HOST','APP_SMTP_USER','APP_SMTP_PASSWORD','APP_EMAIL_FROM'):os.environ.pop(name,None)
        self.assertEqual(self.call('register',email='synthetic@example.test',password='new-long-password',consent=True,adult=True,termsAccepted=True,termsVersion='account-2026-10-12')[0]['statusCode'],503)
        db=app.DB()
        try:self.assertEqual(db.query('SELECT count(*) FROM mh_users').fetchone()[0],0)
        finally:db.close()

    def test_local_delivery_has_no_child_data_and_clears_encrypted_message_after_send(self):
        self.register();token=self.token()
        self.assertEqual(mail_delivery.deliver(app)['delivered'],1)
        files=list(Path(self.directory.name+'/mail').glob('*.eml'));self.assertEqual(len(files),1)
        message=BytesParser(policy=policy.default).parsebytes(files[0].read_bytes())
        self.assertIn(token,message.get_body(preferencelist=('plain',)).get_content())
        db=app.DB()
        try:
            row=db.query('SELECT status,encrypted_message FROM mh_email_outbox').fetchone()
            self.assertEqual(row[0],'sent');self.assertEqual(app.unseal(row[1]),{})
        finally:db.close()
        self.assertEqual(mail_delivery.deliver(app)['delivered'],0)

    def test_failed_delivery_is_retried_without_changing_user_credentials(self):
        cookie,_=self.register();token=self.token()
        with patch.object(mail_delivery,'send',side_effect=RuntimeError('synthetic provider error')):
            self.assertEqual(mail_delivery.deliver(app)['delivered'],0)
        db=app.DB()
        try:
            row=db.query('SELECT status,attempts,lease_until FROM mh_email_outbox').fetchone()
            self.assertEqual(row[:2],('pending',1));self.assertGreater(row[2],int(time.time()))
        finally:db.close()
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],200)
        self.assertEqual(self.call('email-verify',token=token)[0]['statusCode'],200)

    def test_legacy_account_remains_available_and_can_opt_in(self):
        os.environ['APP_EMAIL_VERIFICATION_REQUIRED']='0';cookie,account=self.register()
        os.environ['APP_EMAIL_VERIFICATION_REQUIRED']='1'
        self.assertFalse(self.call('session',cookie)[1]['user']['emailVerificationRequired'])
        self.assertEqual(self.call('save',cookie,state=account['state'],revision=0)[0]['statusCode'],200)
        self.assertEqual(self.call('email-resend',cookie)[0]['statusCode'],200)
        self.assertEqual(self.call('email-verify',token=self.token())[0]['statusCode'],200)

    def test_deleted_account_cascades_mail_tokens_and_queue(self):
        cookie,_=self.register()
        self.assertEqual(self.call('delete',cookie,password='original-long-password')[0]['statusCode'],200)
        db=app.DB()
        try:
            for table in ('mh_email_status','mh_email_tokens','mh_email_outbox'):
                self.assertEqual(db.query('SELECT count(*) FROM '+table).fetchone()[0],0)
        finally:db.close()

    def test_smtp_requires_tls_and_uses_certificate_validation(self):
        os.environ.update(APP_MAIL_DRIVER='smtp',APP_SMTP_HOST='smtp.example.test',APP_SMTP_PORT='587',APP_SMTP_SECURITY='starttls',APP_SMTP_USER='synthetic',APP_SMTP_PASSWORD='synthetic',APP_EMAIL_FROM='sender@example.test')
        smtp=MagicMock();smtp.__enter__.return_value=smtp
        with patch.object(mail_delivery.smtplib,'SMTP',return_value=smtp):
            mail_delivery.send({'to':'synthetic@example.test','subject':'Test','text':'Synthetic'},'synthetic')
        context=smtp.starttls.call_args.kwargs['context'];self.assertTrue(context.check_hostname)
        self.assertEqual(smtp.method_calls[0][0],'ehlo')
        smtp.login.assert_called_once();smtp.send_message.assert_called_once()
        os.environ['APP_SMTP_SECURITY']='none'
        with self.assertRaises(RuntimeError):mail_delivery.send({'to':'synthetic@example.test','subject':'Test','text':'Synthetic'},'synthetic')

    def test_link_origin_is_configured_not_request_controlled(self):
        os.environ['APP_PUBLIC_URL']='http://evil.example.test'
        self.assertEqual(self.call('register',email='synthetic@example.test',password='new-long-password',consent=True,adult=True,termsAccepted=True,termsVersion='account-2026-10-12')[0]['statusCode'],503)


if __name__=='__main__':unittest.main()
